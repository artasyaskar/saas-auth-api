"""
Security Scanning Tool

Comprehensive security scanning tool for the SaaS Auth API.
Includes dependency scanning, code analysis, and vulnerability checks.
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class SecurityScanner:
    """Security scanner for the SaaS Auth API"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = {
            "scan_date": datetime.utcnow().isoformat(),
            "findings": [],
            "summary": {}
        }
    
    def run_all_scans(self) -> Dict[str, Any]:
        """Run all security scans"""
        print("Running comprehensive security scan...")
        
        # Dependency scanning
        self.scan_dependencies()
        
        # Code analysis
        self.scan_code_for_secrets()
        self.scan_code_for_security_issues()
        
        # Configuration checks
        self.check_configurations()
        
        # Permission checks
        self.check_file_permissions()
        
        # Generate summary
        self._generate_summary()
        
        return self.results
    
    def scan_dependencies(self):
        """Scan dependencies for known vulnerabilities"""
        print("\n[1/5] Scanning dependencies...")
        
        try:
            # Try using safety
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                if vulnerabilities:
                    for vuln in vulnerabilities:
                        self.results["findings"].append({
                            "type": "dependency_vulnerability",
                            "severity": "HIGH",
                            "package": vuln.get("package"),
                            "version": vuln.get("version"),
                            "advisory": vuln.get("advisory"),
                            "description": vuln.get("advisory")
                        })
                else:
                    print("  ✓ No known vulnerabilities found")
            else:
                print("  ! Safety scan failed or not installed")
                
        except FileNotFoundError:
            print("  ! Safety not installed. Install with: pip install safety")
    
    def scan_code_for_secrets(self):
        """Scan code for potential secrets and credentials"""
        print("\n[2/5] Scanning for secrets...")
        
        secret_patterns = [
            ("API Key", r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?[a-z0-9]{32,}["\']?'),
            ("Secret Key", r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']?[a-z0-9]{32,}["\']?'),
            ("Password", r'(?i)password\s*[:=]\s*["\']?[^\s"\']{8,}["\']?'),
            ("Token", r'(?i)(token|bearer[_-]?token)\s*[:=]\s*["\']?[a-z0-9]{20,}["\']?'),
            ("AWS Key", r'(?i)aws[_-]?(access[_-]?key[_-]?id|secret[_-]?access[_-]?key)\s*[:=]\s*["\']?[a-z0-9]{20,}["\']?'),
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                for secret_type, pattern in secret_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        self.results["findings"].append({
                            "type": "potential_secret",
                            "severity": "HIGH",
                            "secret_type": secret_type,
                            "file": str(py_file.relative_to(self.project_root)),
                            "matches": len(matches)
                        })
            except Exception:
                pass
        
        secret_findings = [f for f in self.results["findings"] if f["type"] == "potential_secret"]
        if secret_findings:
            print(f"  ! Found {len(secret_findings)} potential secrets")
        else:
            print("  ✓ No secrets found")
    
    def scan_code_for_security_issues(self):
        """Scan code for common security issues"""
        print("\n[3/5] Scanning for security issues...")
        
        security_patterns = [
            ("SQL Injection", r'execute\([^)]*\+[^)]*\)', "HIGH"),
            ("SQL Injection (f-string)", r'execute\(f["\'].*{.*}.*["\']\)', "HIGH"),
            ("Debug Print", r'print\([^)]*password[^)]*\)', "MEDIUM"),
            ("Debug Print", r'print\([^)]*secret[^)]*\)', "MEDIUM"),
            ("Hardcoded Port", r':\s*(8080|3000|5000|8000)', "LOW"),
            ("Weak SSL", r'ssl_context\s*=\s*ssl\._create_unverified_context', "HIGH"),
            ("Eval Usage", r'\beval\s*\(', "HIGH"),
            ("Exec Usage", r'\bexec\s*\(', "HIGH"),
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                for issue_type, pattern, severity in security_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        self.results["findings"].append({
                            "type": "security_issue",
                            "severity": severity,
                            "issue_type": issue_type,
                            "file": str(py_file.relative_to(self.project_root)),
                            "matches": len(matches)
                        })
            except Exception:
                pass
        
        issue_findings = [f for f in self.results["findings"] if f["type"] == "security_issue"]
        if issue_findings:
            print(f"  ! Found {len(issue_findings)} potential security issues")
        else:
            print("  ✓ No security issues found")
    
    def check_configurations(self):
        """Check configuration files for security issues"""
        print("\n[4/5] Checking configurations...")
        
        # Check .env files
        env_files = list(self.project_root.glob(".env*"))
        for env_file in env_files:
            if env_file.name == ".env.example":
                continue
            
            self.results["findings"].append({
                "type": "config_issue",
                "severity": "MEDIUM",
                "issue": "Environment file found in repository",
                "file": str(env_file.relative_to(self.project_root))
            })
        
        # Check for DEBUG=True in settings
        settings_files = list(self.project_root.rglob("settings.py")) + list(self.project_root.rglob("config.py"))
        for settings_file in settings_files:
            try:
                content = settings_file.read_text()
                if "DEBUG = True" in content or "DEBUG=True" in content:
                    self.results["findings"].append({
                        "type": "config_issue",
                        "severity": "HIGH",
                        "issue": "DEBUG mode enabled",
                        "file": str(settings_file.relative_to(self.project_root))
                    })
            except Exception:
                pass
        
        config_findings = [f for f in self.results["findings"] if f["type"] == "config_issue"]
        if config_findings:
            print(f"  ! Found {len(config_findings)} configuration issues")
        else:
            print("  ✓ No configuration issues found")
    
    def check_file_permissions(self):
        """Check file permissions for security issues"""
        print("\n[5/5] Checking file permissions...")
        
        # Check for world-writable files
        try:
            for file_path in self.project_root.rglob("*"):
                if file_path.is_file():
                    mode = file_path.stat().st_mode
                    if mode & 0o002:  # World-writable
                        self.results["findings"].append({
                            "type": "permission_issue",
                            "severity": "MEDIUM",
                            "issue": "World-writable file",
                            "file": str(file_path.relative_to(self.project_root))
                        })
        except Exception:
            pass
        
        perm_findings = [f for f in self.results["findings"] if f["type"] == "permission_issue"]
        if perm_findings:
            print(f"  ! Found {len(perm_findings)} permission issues")
        else:
            print("  ✓ No permission issues found")
    
    def _generate_summary(self):
        """Generate summary of findings"""
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for finding in self.results["findings"]:
            severity = finding.get("severity", "LOW")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        self.results["summary"] = {
            "total_findings": len(self.results["findings"]),
            "by_severity": severity_counts,
            "by_type": {}
        }
        
        for finding in self.results["findings"]:
            ftype = finding.get("type", "unknown")
            self.results["summary"]["by_type"][ftype] = self.results["summary"]["by_type"].get(ftype, 0) + 1
    
    def print_report(self):
        """Print the security scan report"""
        print("\n" + "=" * 60)
        print("SECURITY SCAN REPORT")
        print("=" * 60)
        print(f"Scan Date: {self.results['scan_date']}")
        print(f"Total Findings: {self.results['summary']['total_findings']}")
        print()
        
        print("Findings by Severity:")
        for severity, count in self.results["summary"]["by_severity"].items():
            if count > 0:
                print(f"  {severity}: {count}")
        
        print()
        print("Findings by Type:")
        for ftype, count in self.results["summary"]["by_type"].items():
            print(f"  {ftype}: {count}")
        
        if self.results["findings"]:
            print("\nDetailed Findings:")
            print("-" * 60)
            for i, finding in enumerate(self.results["findings"], 1):
                print(f"\n[{i}] {finding.get('type', 'unknown').upper()}")
                print(f"    Severity: {finding.get('severity', 'LOW')}")
                print(f"    File: {finding.get('file', 'N/A')}")
                for key, value in finding.items():
                    if key not in ["type", "severity", "file"]:
                        print(f"    {key}: {value}")
        
        print("\n" + "=" * 60)
    
    def save_report(self, output_file: str):
        """Save the report to a file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nReport saved to: {output_file}")


def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent
    
    scanner = SecurityScanner(str(project_root))
    results = scanner.run_all_scans()
    scanner.print_report()
    
    # Save report
    report_file = project_root / "security_scan_report.json"
    scanner.save_report(str(report_file))
    
    # Exit with error code if high/critical findings
    high_severity = results["summary"]["by_severity"].get("HIGH", 0)
    critical_severity = results["summary"]["by_severity"].get("CRITICAL", 0)
    
    if high_severity > 0 or critical_severity > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
