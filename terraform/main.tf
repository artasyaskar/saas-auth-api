# Terraform configuration for SaaS Auth API infrastructure
# This configuration provisions AWS resources for production deployment

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket         = "saas-auth-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "saas-auth-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
        Project     = "saas-auth-api"
        Environment = var.environment
        ManagedBy   = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_ca_certificate)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs              = data.aws_availability_zones.available.names
  private_subnets  = var.private_subnet_cidrs
  public_subnets   = var.public_subnet_cidrs
  database_subnets = var.database_subnet_cidrs

  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true

  enable_vpn_gateway = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC endpoints for private subnets
  vpc_endpoint_enabled = true
  vpc_endpoints = {
    s3 = {
      service_name = "com.amazonaws.${var.aws_region}.s3"
    }
    dynamodb = {
      service_name = "com.amazonaws.${var.aws_region}.dynamodb"
    }
    ec2 = {
      service_name = "com.amazonaws.${var.aws_region}.ec2"
    }
    ecs = {
      service_name = "com.amazonaws.${var.aws_region}.ecs"
    }
    ecs_telemetry = {
      service_name = "com.amazonaws.${var.aws_region}.ecs-telemetry"
    }
    ecs_agent = {
      service_name = "com.amazonaws.${var.aws_region}.ecs-agent"
    }
  }

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# EKS Cluster Module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${var.project_name}-cluster"
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    general = {
      name           = "general-node-group"
      instance_types = ["t3.large", "t3a.large"]
      min_size       = 3
      max_size       = 10
      desired_size   = 3

      labels = {
        role = "general"
      }

      taints = []
    }

    compute = {
      name           = "compute-node-group"
      instance_types = ["m5.large", "m5a.large"]
      min_size       = 2
      max_size       = 20
      desired_size   = 5

      labels = {
        role = "compute"
      }

      taints = []
    }

    database = {
      name           = "database-node-group"
      instance_types = ["r5.large", "r5a.large"]
      min_size       = 1
      max_size       = 5
      desired_size   = 2

      labels = {
        role = "database"
      }

      taints = [
        {
          key    = "dedicated"
          value  = "database"
          effect = "NO_SCHEDULE"
        }
      ]
    }
  }

  # Cluster security group rules
  cluster_security_group_additional_rules = {
    ingress_nodes_ephemeral_ports_tcp = {
      description                = "Nodes on ephemeral ports"
      protocol                   = "tcp"
      from_port                  = 1025
      to_port                    = 65535
      type                       = "ingress"
      source_node_security_group = true
    }
  }

  tags = {
    Environment = var.environment
  }
}

# RDS PostgreSQL
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${var.project_name}-postgres"

  engine               = "postgres"
  engine_version       = "14.9"
  family               = "postgres14"
  major_engine_version = "14"
  instance_class       = "db.r6g.xlarge"
  allocated_storage    = 100
  storage_encrypted    = true
  storage_type         = "gp3"

  db_name  = "saas_auth"
  username = var.db_username
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.security_groups.rds_sg_id]

  maintenance_window = "Mon:00:00-Mon:03:00"
  backup_window      = "03:00-06:00"
  backup_retention_period = 30

  performance_insights_enabled = true
  monitoring_interval         = 60

  deletion_protection = true
  skip_final_snapshot  = false

  parameters = [
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "262144" # 256MB
    },
    {
      name  = "effective_cache_size"
      value = "786432" # 768MB
    }
  ]

  tags = {
    Environment = var.environment
  }
}

# ElastiCache Redis Cluster
module "elasticache" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  cluster_id      = "${var.project_name}-redis"
  engine_version  = "7.0"
  node_type       = "cache.r6g.large"
  num_cache_nodes = 3

  subnet_group_name  = module.vpc.redis_subnet_group_name
  security_group_ids = [module.security_groups.redis_sg_id]

  parameter_group_name = aws_elasticache_parameter_group.default.name

  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true

  auth_token = var.redis_auth_token

  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"

  tags = {
    Environment = var.environment
  }
}

resource "aws_elasticache_parameter_group" "default" {
  family = "redis7"
  name   = "${var.project_name}-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }
}

# Security Groups
module "security_groups" {
  source = "./modules/security_groups"

  vpc_id     = module.vpc.vpc_id
  vpc_cidr   = var.vpc_cidr
  project_name = var.project_name
}

# S3 Bucket for backups and static assets
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-backups-${var.aws_region}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "backup-lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/eks/${var.project_name}/application"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "nginx_logs" {
  name              = "/aws/eks/${var.project_name}/nginx"
  retention_in_days = 30
}

# IAM Roles for Service Accounts (IRSA)
module "irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role-with-oidc"
  version = "~> 5.0"

  create_role = true

  role_name_prefix = "${var.project_name}-"

  provider_url = module.eks.oidc_provider
  role_policy_arns = {
    s3_access = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
  }

  oidc_fully_qualified_subjects = [
    "system:serviceaccount:saas-auth-prod:*"
  ]
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_ca_certificate" {
  description = "EKS cluster CA certificate"
  value       = module.eks.cluster_ca_certificate
}

output "database_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
}

output "redis_endpoint" {
  description = "ElastiCache endpoint"
  value       = module.elasticache.redis_endpoint
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}
