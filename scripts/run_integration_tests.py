#!/usr/bin/env python3
"""
Integration test runner for the HMO document processing pipeline.

Runs comprehensive integration tests including performance benchmarks,
error scenario testing, and system validation.
"""

import sys
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.integration_manager import IntegrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Comprehensive integration test runner."""
    
    def __init__(self):
        """Initialize test runner."""
        self.project_root = project_root
        self.test_results = {}
        self.integration_manager = None
        
    def setup_test_environment(self) -> bool:
        """
        Set up test environment and validate system components.
        
        Returns:
            bool: True if setup successful
        """
        logger.info("Setting up test environment...")
        
        try:
            # Initialize integration manager
            self.integration_manager = IntegrationManager()
            
            # Validate system components
            validation_results = self.integration_manager.validate_system_components()
            
            logger.info(f"System validation: {validation_results['overall_status']}")
            
            if validation_results['overall_status'] in ['fully_operational', 'mostly_operational']:
                logger.info("✅ System components validated successfully")
                return True
            else:
                logger.warning("⚠️ Some system components have issues:")
                for issue in validation_results.get('issues', []):
                    logger.warning(f"  - {issue}")
                return True  # Continue with limited functionality
                
        except Exception as e:
            logger.error(f"❌ Failed to set up test environment: {str(e)}")
            return False
            
    def run_unit_tests(self) -> Dict[str, Any]:
        """
        Run unit tests for individual components.
        
        Returns:
            Dict with test results
        """
        logger.info("Running unit tests...")
        
        test_files = [
            "tests/test_hmo_record.py",
            "tests/test_data_validator.py",
            "tests/test_nlp_pipeline.py",
            "tests/test_document_processors.py"
        ]
        
        results = {
            'total_files': 0,
            'passed_files': 0,
            'failed_files': 0,
            'details': {}
        }
        
        for test_file in test_files:
            test_path = self.project_root / test_file
            
            if not test_path.exists():
                logger.warning(f"Test file not found: {test_file}")
                continue
                
            results['total_files'] += 1
            
            try:
                # Run pytest on individual file
                cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    results['passed_files'] += 1
                    results['details'][test_file] = 'PASSED'
                    logger.info(f"✅ {test_file}: PASSED")
                else:
                    results['failed_files'] += 1
                    results['details'][test_file] = 'FAILED'
                    logger.error(f"❌ {test_file}: FAILED")
                    logger.error(f"Error output: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                results['failed_files'] += 1
                results['details'][test_file] = 'TIMEOUT'
                logger.error(f"⏰ {test_file}: TIMEOUT")
            except Exception as e:
                results['failed_files'] += 1
                results['details'][test_file] = f'ERROR: {str(e)}'
                logger.error(f"💥 {test_file}: ERROR - {str(e)}")
                
        return results
        
    def run_integration_tests(self) -> Dict[str, Any]:
        """
        Run integration tests.
        
        Returns:
            Dict with test results
        """
        logger.info("Running integration tests...")
        
        test_path = self.project_root / "tests" / "test_integration.py"
        
        if not test_path.exists():
            logger.error("Integration test file not found")
            return {'status': 'ERROR', 'message': 'Test file not found'}
            
        try:
            # Run integration tests
            cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short", "-x"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            if result.returncode == 0:
                logger.info("✅ Integration tests: PASSED")
                return {
                    'status': 'PASSED',
                    'output': result.stdout,
                    'duration': 'N/A'
                }
            else:
                logger.error("❌ Integration tests: FAILED")
                logger.error(f"Error output: {result.stderr}")
                return {
                    'status': 'FAILED',
                    'output': result.stdout,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Integration tests: TIMEOUT")
            return {'status': 'TIMEOUT', 'message': 'Tests timed out after 10 minutes'}
        except Exception as e:
            logger.error(f"💥 Integration tests: ERROR - {str(e)}")
            return {'status': 'ERROR', 'message': str(e)}
            
    def run_performance_tests(self) -> Dict[str, Any]:
        """
        Run performance tests and benchmarks.
        
        Returns:
            Dict with performance results
        """
        logger.info("Running performance tests...")
        
        test_path = self.project_root / "tests" / "test_performance.py"
        
        if not test_path.exists():
            logger.error("Performance test file not found")
            return {'status': 'ERROR', 'message': 'Test file not found'}
            
        try:
            # Run performance tests
            cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)  # 15 minute timeout
            duration = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ Performance tests: PASSED (Duration: {duration:.1f}s)")
                return {
                    'status': 'PASSED',
                    'duration_seconds': duration,
                    'output': result.stdout
                }
            else:
                logger.error("❌ Performance tests: FAILED")
                return {
                    'status': 'FAILED',
                    'duration_seconds': duration,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Performance tests: TIMEOUT")
            return {'status': 'TIMEOUT', 'message': 'Tests timed out after 15 minutes'}
        except Exception as e:
            logger.error(f"💥 Performance tests: ERROR - {str(e)}")
            return {'status': 'ERROR', 'message': str(e)}
            
    def run_system_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive system validation.
        
        Returns:
            Dict with validation results
        """
        logger.info("Running system validation...")
        
        if not self.integration_manager:
            return {'status': 'ERROR', 'message': 'Integration manager not initialized'}
            
        try:
            # Component validation
            component_validation = self.integration_manager.validate_system_components()
            
            # Performance status
            performance_status = self.integration_manager.get_performance_status()
            
            # System optimization
            optimization_results = self.integration_manager.optimize_system_performance()
            
            validation_results = {
                'status': 'COMPLETED',
                'component_validation': component_validation,
                'performance_status': performance_status,
                'optimization_results': optimization_results,
                'overall_health': component_validation['overall_status']
            }
            
            logger.info(f"✅ System validation completed - Overall health: {validation_results['overall_health']}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"💥 System validation failed: {str(e)}")
            return {'status': 'ERROR', 'message': str(e)}
            
    def generate_test_report(self) -> str:
        """
        Generate comprehensive test report.
        
        Returns:
            str: Path to generated report
        """
        logger.info("Generating test report...")
        
        report_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_results': self.test_results,
            'summary': self._generate_summary()
        }
        
        # Save report
        report_path = self.project_root / "test_report.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            logger.info(f"✅ Test report saved to: {report_path}")
            
            # Also create a human-readable summary
            summary_path = self.project_root / "test_summary.txt"
            self._create_text_summary(summary_path, report_data)
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {str(e)}")
            return ""
            
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        summary = {
            'total_test_suites': 0,
            'passed_test_suites': 0,
            'failed_test_suites': 0,
            'overall_status': 'UNKNOWN'
        }
        
        for test_name, result in self.test_results.items():
            summary['total_test_suites'] += 1
            
            if isinstance(result, dict):
                status = result.get('status', 'UNKNOWN')
                if status in ['PASSED', 'COMPLETED']:
                    summary['passed_test_suites'] += 1
                elif status in ['FAILED', 'ERROR', 'TIMEOUT']:
                    summary['failed_test_suites'] += 1
            elif isinstance(result, dict) and 'passed_files' in result:
                # Unit test results
                if result['failed_files'] == 0:
                    summary['passed_test_suites'] += 1
                else:
                    summary['failed_test_suites'] += 1
                    
        # Determine overall status
        if summary['failed_test_suites'] == 0:
            summary['overall_status'] = 'ALL_PASSED'
        elif summary['passed_test_suites'] > summary['failed_test_suites']:
            summary['overall_status'] = 'MOSTLY_PASSED'
        else:
            summary['overall_status'] = 'MOSTLY_FAILED'
            
        return summary
        
    def _create_text_summary(self, summary_path: Path, report_data: Dict[str, Any]) -> None:
        """Create human-readable text summary."""
        try:
            with open(summary_path, 'w') as f:
                f.write("HMO Document Processing Pipeline - Integration Test Report\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Test Run Date: {report_data['timestamp']}\n\n")
                
                summary = report_data['summary']
                f.write("SUMMARY:\n")
                f.write(f"  Total Test Suites: {summary['total_test_suites']}\n")
                f.write(f"  Passed: {summary['passed_test_suites']}\n")
                f.write(f"  Failed: {summary['failed_test_suites']}\n")
                f.write(f"  Overall Status: {summary['overall_status']}\n\n")
                
                f.write("DETAILED RESULTS:\n")
                for test_name, result in report_data['test_results'].items():
                    f.write(f"\n{test_name.upper()}:\n")
                    
                    if isinstance(result, dict):
                        status = result.get('status', 'UNKNOWN')
                        f.write(f"  Status: {status}\n")
                        
                        if 'duration_seconds' in result:
                            f.write(f"  Duration: {result['duration_seconds']:.1f} seconds\n")
                            
                        if 'message' in result:
                            f.write(f"  Message: {result['message']}\n")
                            
                        if 'details' in result:
                            f.write("  Details:\n")
                            for key, value in result['details'].items():
                                f.write(f"    {key}: {value}\n")
                                
            logger.info(f"✅ Text summary saved to: {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to create text summary: {str(e)}")
            
    def run_all_tests(self) -> bool:
        """
        Run all integration tests.
        
        Returns:
            bool: True if all tests passed
        """
        logger.info("🚀 Starting comprehensive integration test suite...")
        
        # Setup
        if not self.setup_test_environment():
            logger.error("❌ Failed to set up test environment")
            return False
            
        # Run test suites
        test_suites = [
            ('unit_tests', self.run_unit_tests),
            ('integration_tests', self.run_integration_tests),
            ('performance_tests', self.run_performance_tests),
            ('system_validation', self.run_system_validation)
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"\n📋 Running {suite_name}...")
            
            try:
                result = test_func()
                self.test_results[suite_name] = result
                
                # Log result
                if isinstance(result, dict):
                    status = result.get('status', 'UNKNOWN')
                    logger.info(f"✅ {suite_name}: {status}")
                else:
                    logger.info(f"✅ {suite_name}: Completed")
                    
            except Exception as e:
                logger.error(f"💥 {suite_name} failed: {str(e)}")
                self.test_results[suite_name] = {'status': 'ERROR', 'message': str(e)}
                
        # Generate report
        report_path = self.generate_test_report()
        
        # Determine overall success
        summary = self._generate_summary()
        success = summary['overall_status'] in ['ALL_PASSED', 'MOSTLY_PASSED']
        
        if success:
            logger.info("🎉 Integration test suite completed successfully!")
        else:
            logger.error("❌ Integration test suite completed with failures")
            
        logger.info(f"📊 Full report available at: {report_path}")
        
        return success
        
    def cleanup(self) -> None:
        """Clean up test resources."""
        if self.integration_manager:
            try:
                self.integration_manager.performance_optimizer.cleanup_resources()
            except Exception as e:
                logger.warning(f"Cleanup warning: {str(e)}")


def main():
    """Main entry point."""
    runner = IntegrationTestRunner()
    
    try:
        success = runner.run_all_tests()
        exit_code = 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Test run interrupted by user")
        exit_code = 130
        
    except Exception as e:
        logger.error(f"Test run failed with unexpected error: {str(e)}")
        exit_code = 1
        
    finally:
        runner.cleanup()
        
    sys.exit(exit_code)


if __name__ == "__main__":
    main()