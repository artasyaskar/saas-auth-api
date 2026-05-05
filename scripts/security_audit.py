#!/usr/bin/env python3
"""
Security Audit Script

Performs automated security checks on the codebase.
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple


class SecurityAuditor:
    """Automated security auditing tool."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []
        
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all security checks."""
        print("🔍 Starting Security Audit...\n")
        
        self.check_for_secrets()
        self.check_file_permissions()
        self.check_dependencies()
        self.check_configuration()
        self.check_code_patterns()
        self.check_database_security()
        
        return self.generate_report()
    
    def check_for_secrets(self):
        """Check for hardcoded secrets in code."""
        print("📋 Checking for hardcoded secrets...")
        
        secret_patterns = [
            (r'secret_key\s*=\s*["\'][^"\']+["\']', "Hardcoded SECRET_KEY"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'aws_access_key_id\s*=\s*["\'][^"\']+["\']', "AWS Access Key"),
            (r'private_key\s*=\s*["\'][^"\']+["\']', "Private key"),
            (r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', "Potential token"),
        ]
        
        python_files = list(self.project_path.rglob("*.py"))
        
        for file_path in python_files:
            if '.git' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                for pattern, description in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip test files and example configs
                        if 'test' in str(file_path).lower() or 'example' in str(file_path).lower():
                            continue
                            
                        self.issues.append({
                            "severity": "HIGH",
                            "category": "Secrets Management",
                            "description": description,
                            "file": str(file_path),
                            "line": content[:match.start()].count('\n') + 1,
                            "recommendation": "Use environment variables or secrets manager"
                        })
            except Exception as e:
                self.warnings.append({
                    "category": "File Access",
                    "description": f"Could not read {file_path}: {e}"
                })
        
        # Check .env files in git
        if self._run_command("git ls-files | grep -E '\.env'", shell=True):
            self.issues.append({
                "severity": "CRITICAL",
                "category": "Secrets Management",
                "description": ".env files committed to git",
                "recommendation": "Remove from git and add to .gitignore"
            })
        
        print(f"   Found {len([i for i in self.issues if i.get('category') == 'Secrets Management'])} potential secrets issues")
    
    def check_file_permissions(self):
        """Check file permissions."""
        print("📋 Checking file permissions...")
        
        sensitive_files = [
            ".env",
            "*.pem",
            "*.key",
            "id_rsa",
            ".htpasswd"
        ]
        
        for pattern in sensitive_files:
            files = list(self.project_path.rglob(pattern))
            for file_path in files:
                try:
                    stat = file_path.stat()
                    mode = stat.st_mode
                    # Check if world-readable
                    if mode & 0o044:
                        self.warnings.append({
                            "severity": "MEDIUM",
                            "category": "File Permissions",
                            "description": f"{file_path} is world-readable",
                            "recommendation": f"chmod 600 {file_path}"
                        })
                except Exception:
                    pass
        
        print(f"   Found {len([w for w in self.warnings if w.get('category') == 'File Permissions'])} permission issues")
    
    def check_dependencies(self):
        """Check dependencies for known vulnerabilities."""
        print("📋 Checking dependencies...")
        
        # Check for safety
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            if result.returncode != 0 and result.stdout:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities.get("vulnerabilities", []):
                    self.issues.append({
                        "severity": vuln.get("severity", "MEDIUM").upper(),
                        "category": "Dependencies",
                        "description": f"{vuln.get('package_name')} {vuln.get('vulnerable_spec')}: {vuln.get('advisory')}",
                        "recommendation": f"Upgrade to {vuln.get('analyzed_spec')}"
                    })
        except FileNotFoundError:
            self.info.append({
                "category": "Tools",
                "description": "safety not installed. Run: pip install safety"
            })
        except Exception as e:
            self.warnings.append({
                "category": "Dependencies",
                "description": f"Could not check dependencies: {e}"
            })
        
        # Check for bandit
        try:
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json", "-o", "/dev/stdout"],
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                for issue in bandit_results.get("results", []):
                    self.issues.append({
                        "severity": issue.get("issue_severity", "MEDIUM"),
                        "category": "Code Security",
                        "description": issue.get("issue_text"),
                        "file": issue.get("filename"),
                        "line": issue.get("line_number"),
                        "recommendation": f"See CWE: {issue.get('issue_cwe', {}).get('id', 'N/A')}"
                    })
        except FileNotFoundError:
            self.info.append({
                "category": "Tools",
                "description": "bandit not installed. Run: pip install bandit"
            })
        
        dep_issues = len([i for i in self.issues if i.get('category') in ['Dependencies', 'Code Security']])
        print(f"   Found {dep_issues} dependency/code security issues")
    
    def check_configuration(self):
        """Check configuration security."""
        print("📋 Checking configuration...")
        
        # Check for DEBUG mode in production
        env_file = self.project_path / ".env"
        if env_file.exists():
            content = env_file.read_text()
            if 'DEBUG=true' in content and 'APP_ENV=production' in content:
                self.issues.append({
                    "severity": "HIGH",
                    "category": "Configuration",
                    "description": "DEBUG mode enabled in production configuration",
                    "recommendation": "Set DEBUG=false in production"
                })
        
        # Check for weak secret key
        if env_file.exists():
            content = env_file.read_text()
            secret_match = re.search(r'SECRET_KEY=(.+)', content)
            if secret_match:
                secret = secret_match.group(1)
                if len(secret) < 32 or secret in ['change-me', 'secret', 'default']:
                    self.issues.append({
                        "severity": "CRITICAL",
                        "category": "Configuration",
                        "description": "Weak or default SECRET_KEY detected",
                        "recommendation": "Generate strong secret: openssl rand -base64 32"
                    })
        
        # Check Docker security
        dockerfile = self.project_path / "Dockerfile"
        if dockerfile.exists():
            content = dockerfile.read_text()
            if 'USER root' in content and 'USER ' not in content.split('USER root')[-1]:
                self.warnings.append({
                    "severity": "MEDIUM",
                    "category": "Configuration",
                    "description": "Docker container runs as root",
                    "recommendation": "Add 'USER appuser' directive"
                })
        
        config_issues = len([i for i in self.issues if i.get('category') == 'Configuration'])
        print(f"   Found {config_issues} configuration issues")
    
    def check_code_patterns(self):
        """Check for insecure code patterns."""
        print("📋 Checking code patterns...")
        
        insecure_patterns = [
            (r'eval\s*\(', "Use of eval()", "CRITICAL"),
            (r'exec\s*\(', "Use of exec()", "CRITICAL"),
            (r'subprocess\.call.*shell\s*=\s*True', "Shell=True in subprocess", "HIGH"),
            (r'pickle\.loads?', "Unsafe deserialization with pickle", "HIGH"),
            (r'yaml\.load\([^)]*\)(?!.*Loader)', "Unsafe YAML loading", "HIGH"),
            (r'request\.args\[', "Direct request parameter access", "MEDIUM"),
            (r'string\.format\(.*\)', "Potential format string vulnerability", "MEDIUM"),
            (r'\.format\s*\(\s*.*%.*\)', "Potential format string vulnerability", "MEDIUM"),
            (r'print\s*\(.*password', "Password in print statement", "HIGH"),
            (r'logger\.(debug|info|warning|error).*password', "Password in logs", "HIGH"),
        ]
        
        python_files = list(self.project_path.rglob("*.py"))
        
        for file_path in python_files:
            if '.git' in str(file_path) or 'test' in str(file_path).lower():
                continue
                
            try:
                content = file_path.read_text()
                for pattern, description, severity in insecure_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        self.issues.append({
                            "severity": severity,
                            "category": "Code Security",
                            "description": description,
                            "file": str(file_path),
                            "line": content[:match.start()].count('\n') + 1,
                            "recommendation": "Review and refactor to secure alternative"
                        })
            except Exception:
                pass
        
        # Check SQL injection risks
        sql_patterns = [
            (r'execute\s*\(.*\+', "Potential SQL injection"),
            (r'execute\s*\(.*%.*', "Potential SQL injection"),
            (r'execute\s*\(.*\.format', "Potential SQL injection"),
            (r'f["\'].*SELECT.*{.*}.*["\']', "Potential SQL injection with f-string"),
        ]
        
        for file_path in python_files:
            if '.git' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                for pattern, description in sql_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        self.issues.append({
                            "severity": "CRITICAL",
                            "category": "SQL Injection",
                            "description": description,
                            "file": str(file_path),
                            "line": content[:match.start()].count('\n') + 1,
                            "recommendation": "Use parameterized queries or ORM"
                        })
            except Exception:
                pass
        
        code_issues = len([i for i in self.issues if i.get('category') == 'Code Security'])
        print(f"   Found {code_issues} code security issues")
    
    def check_database_security(self):
        """Check database security configurations."""
        print("📋 Checking database security...")
        
        # Check for database URL in code
        python_files = list(self.project_path.rglob("*.py"))
        
        for file_path in python_files:
            if '.git' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                if re.search(r'postgresql://[^:]+:[^@]+@', content):
                    self.warnings.append({
                        "severity": "HIGH",
                        "category": "Database Security",
                        "description": f"Database credentials may be hardcoded in {file_path}",
                        "recommendation": "Use environment variables for database URLs"
                    })
            except Exception:
                pass
        
        db_issues = len([w for w in self.warnings if w.get('category') == 'Database Security'])
        print(f"   Found {db_issues} database security issues")
    
    def _run_command(self, command: str, shell: bool = False) -> bool:
        """Run shell command and return success status."""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                cwd=self.project_path
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security audit report."""
        critical = len([i for i in self.issues if i.get("severity") == "CRITICAL"])
        high = len([i for i in self.issues if i.get("severity") == "HIGH"])
        medium = len([i for i in self.issues if i.get("severity") == "MEDIUM"])
        low = len([i for i in self.issues if i.get("severity") == "LOW"])
        
        report = {
            "metadata": {
                "audit_date": datetime.utcnow().isoformat(),
                "project_path": str(self.project_path.absolute()),
                "auditor": "SaaS Auth API Security Scanner"
            },
            "summary": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
                "total_issues": len(self.issues),
                "total_warnings": len(self.warnings),
                "risk_score": self._calculate_risk_score(critical, high, medium, low)
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _calculate_risk_score(self, critical: int, high: int, medium: int, low: int) -> int:
        """Calculate overall risk score (0-100, lower is better)."""
        score = 100
        score -= critical * 25
        score -= high * 10
        score -= medium * 5
        score -= low * 1
        return max(0, score)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate overall security recommendations."""
        recommendations = []
        
        if any(i.get("category") == "Secrets Management" for i in self.issues):
            recommendations.append("Implement secrets management (Vault, AWS Secrets Manager)")
        
        if any(i.get("category") == "Dependencies" for i in self.issues):
            recommendations.append("Set up automated dependency vulnerability scanning")
        
        if any(i.get("category") == "Code Security" for i in self.issues):
            recommendations.append("Integrate security scanning in CI/CD pipeline")
        
        if not recommendations:
            recommendations.append("Continue regular security audits and monitoring")
        
        return recommendations
    
    def print_report(self, report: Dict[str, Any]):
        """Print human-readable report."""
        print("\n" + "=" * 60)
        print("SECURITY AUDIT REPORT")
        print("=" * 60)
        print(f"\nAudit Date: {report['metadata']['audit_date']}")
        print(f"Risk Score: {report['summary']['risk_score']}/100")
        print("\nSummary:")
        print(f"  🔴 Critical: {report['summary']['critical']}")
        print(f"  🟠 High: {report['summary']['high']}")
        print(f"  🟡 Medium: {report['summary']['medium']}")
        print(f"  🔵 Low: {report['summary']['low']}")
        print(f"\nTotal Issues: {report['summary']['total_issues']}")
        print(f"Total Warnings: {report['summary']['total_warnings']}")
        
        if report['issues']:
            print("\n" + "-" * 60)
            print("ISSUES:")
            print("-" * 60)
            for issue in sorted(report['issues'], 
                              key=lambda x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(x.get('severity', 'LOW'))):
                print(f"\n[{issue['severity']}] {issue['category']}")
                print(f"  Description: {issue['description']}")
                if 'file' in issue:
                    print(f"  File: {issue['file']}:{issue.get('line', 'N/A')}")
                print(f"  Recommendation: {issue['recommendation']}")
        
        if report['recommendations']:
            print("\n" + "-" * 60)
            print("RECOMMENDATIONS:")
            print("-" * 60)
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        print("\n" + "=" * 60)
        print("End of Report")
        print("=" * 60 + "\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Audit Tool")
    parser.add_argument("--project", default=".", help="Project path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Output file")
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(args.project)
    report = auditor.run_all_checks()
    
    if args.json:
        output = json.dumps(report, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report saved to {args.output}")
        else:
            print(output)
    else:
        auditor.print_report(report)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"JSON report saved to {args.output}")
    
    # Exit with error code if critical/high issues found
    critical_high = report['summary']['critical'] + report['summary']['high']
    if critical_high > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
