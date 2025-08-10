#!/usr/bin/env python3
"""
WebSocket Performance Test Runner
Comprehensive performance testing suite for high-scale WebSocket optimization
"""

import asyncio
import json
import logging
import time
import argparse
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.performance.websocket_optimizer import HighPerformanceWebSocketManager
from tests.performance.load_test_websocket import LoadTestConfig, run_websocket_load_test
from monitoring.websocket_metrics import WebSocketMetricsCollector

logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Comprehensive performance test suite"""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8765):
        self.server_host = server_host
        self.server_port = server_port
        self.server_manager = None
        self.test_results = []
        
    async def run_all_tests(self, quick_mode: bool = False) -> Dict:
        """Run all performance tests"""
        logger.info("Starting comprehensive WebSocket performance test suite")
        
        # Start optimized WebSocket server
        await self._start_test_server()
        
        try:
            # Test configurations
            test_configs = self._get_test_configurations(quick_mode)
            
            # Run each test
            for test_name, config in test_configs.items():
                logger.info(f"Running test: {test_name}")
                
                try:
                    result = await run_websocket_load_test(config)
                    result_dict = result.to_dict()
                    result_dict['test_name'] = test_name
                    self.test_results.append(result_dict)
                    
                    logger.info(f"Test {test_name} completed - Grade: {result._calculate_performance_grade()}")
                    
                    # Brief pause between tests
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Test {test_name} failed: {e}")
                    self.test_results.append({
                        'test_name': test_name,
                        'error': str(e),
                        'status': 'failed'
                    })
            
            # Generate comprehensive report
            report = self._generate_comprehensive_report()
            
            return report
            
        finally:
            # Stop test server
            await self._stop_test_server()
    
    async def _start_test_server(self):
        """Start optimized WebSocket server for testing"""
        logger.info("Starting high-performance WebSocket test server")
        
        self.server_manager = HighPerformanceWebSocketManager(
            host=self.server_host,
            port=self.server_port,
            max_connections=2000
        )
        
        success = await self.server_manager.start_server()
        if not success:
            raise RuntimeError("Failed to start WebSocket test server")
        
        # Wait for server to be ready
        await asyncio.sleep(2)
        
        logger.info(f"Test server started on ws://{self.server_host}:{self.server_port}")
    
    async def _stop_test_server(self):
        """Stop WebSocket test server"""
        if self.server_manager:
            await self.server_manager.stop_server()
            logger.info("Test server stopped")
    
    def _get_test_configurations(self, quick_mode: bool) -> Dict[str, LoadTestConfig]:
        """Get test configurations for different scenarios"""
        if quick_mode:
            return {
                "quick_baseline": LoadTestConfig(
                    server_host=self.server_host,
                    server_port=self.server_port,
                    max_connections=100,
                    test_duration_seconds=60,
                    messages_per_connection_per_minute=10,
                    target_latency_p95_ms=100.0,
                    target_throughput_msg_per_sec=100.0
                ),
                "quick_stress": LoadTestConfig(
                    server_host=self.server_host,
                    server_port=self.server_port,
                    max_connections=500,
                    test_duration_seconds=120,
                    messages_per_connection_per_minute=20,
                    target_latency_p95_ms=150.0,
                    target_throughput_msg_per_sec=500.0
                )
            }
        
        return {
            "baseline_performance": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=100,
                test_duration_seconds=180,
                messages_per_connection_per_minute=10,
                target_latency_p95_ms=50.0,
                target_throughput_msg_per_sec=100.0,
                enable_stress_test=False,
                enable_spike_test=False,
                enable_endurance_test=True,
                enable_connection_churn_test=False
            ),
            
            "moderate_load": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=500,
                test_duration_seconds=300,
                messages_per_connection_per_minute=15,
                target_latency_p95_ms=75.0,
                target_throughput_msg_per_sec=500.0,
                enable_stress_test=True,
                enable_spike_test=True,
                enable_endurance_test=True,
                enable_connection_churn_test=True
            ),
            
            "high_load": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=1000,
                test_duration_seconds=300,
                messages_per_connection_per_minute=20,
                target_latency_p95_ms=100.0,
                target_throughput_msg_per_sec=1000.0,
                enable_stress_test=True,
                enable_spike_test=True,
                enable_endurance_test=True,
                enable_connection_churn_test=True
            ),
            
            "extreme_load": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=2000,
                test_duration_seconds=300,
                messages_per_connection_per_minute=25,
                target_latency_p95_ms=150.0,
                target_throughput_msg_per_sec=2000.0,
                enable_stress_test=True,
                enable_spike_test=True,
                enable_endurance_test=True,
                enable_connection_churn_test=True
            ),
            
            "message_throughput": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=500,
                test_duration_seconds=180,
                messages_per_connection_per_minute=60,  # High message rate
                message_size_bytes=512,
                target_latency_p95_ms=100.0,
                target_throughput_msg_per_sec=2000.0,
                enable_stress_test=True,
                enable_spike_test=False,
                enable_endurance_test=False,
                enable_connection_churn_test=False
            ),
            
            "connection_stability": LoadTestConfig(
                server_host=self.server_host,
                server_port=self.server_port,
                max_connections=1000,
                test_duration_seconds=600,  # 10 minutes
                messages_per_connection_per_minute=5,   # Low message rate
                target_latency_p95_ms=100.0,
                target_throughput_msg_per_sec=500.0,
                enable_stress_test=False,
                enable_spike_test=False,
                enable_endurance_test=True,
                enable_connection_churn_test=True
            )
        }
    
    def _generate_comprehensive_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Filter successful tests
        successful_tests = [r for r in self.test_results if 'error' not in r]
        failed_tests = [r for r in self.test_results if 'error' in r]
        
        if not successful_tests:
            return {
                "status": "failed",
                "message": "All tests failed",
                "failed_tests": failed_tests,
                "timestamp": datetime.now().isoformat()
            }
        
        # Aggregate metrics
        total_connections_tested = sum(r['connection_metrics']['total_attempted'] for r in successful_tests)
        total_messages_sent = sum(r['message_metrics']['total_sent'] for r in successful_tests)
        
        # Performance metrics
        avg_p95_latency = sum(r['latency_metrics']['p95_ms'] for r in successful_tests) / len(successful_tests)
        avg_p99_latency = sum(r['latency_metrics']['p99_ms'] for r in successful_tests) / len(successful_tests)
        max_throughput = max(r['message_metrics']['messages_per_second'] for r in successful_tests)
        avg_error_rate = sum(r['error_metrics']['connection_error_rate'] for r in successful_tests) / len(successful_tests)
        
        # Resource usage
        peak_cpu = max(r['resource_usage']['peak_cpu_usage'] for r in successful_tests)
        peak_memory = max(r['resource_usage']['peak_memory_mb'] for r in successful_tests)
        
        # Performance grades
        grades = [r['performance_grade'] for r in successful_tests]
        grade_counts = {grade: grades.count(grade) for grade in set(grades)}
        
        # Determine overall performance level
        if avg_p95_latency <= 100 and max_throughput >= 1000 and avg_error_rate <= 1.0:
            performance_level = "EXCELLENT"
        elif avg_p95_latency <= 150 and max_throughput >= 500 and avg_error_rate <= 2.0:
            performance_level = "GOOD"
        elif avg_p95_latency <= 200 and max_throughput >= 250 and avg_error_rate <= 5.0:
            performance_level = "ACCEPTABLE"
        else:
            performance_level = "NEEDS_IMPROVEMENT"
        
        # Check if targets are met for 1000+ concurrent users
        high_load_tests = [r for r in successful_tests if r['config']['max_connections'] >= 1000]
        meets_1000_user_target = False
        
        if high_load_tests:
            best_1000_test = min(high_load_tests, key=lambda r: r['latency_metrics']['p95_ms'])
            meets_1000_user_target = (
                best_1000_test['latency_metrics']['p95_ms'] <= 100 and
                best_1000_test['error_metrics']['connection_error_rate'] <= 1.0 and
                best_1000_test['test_results']['overall_success']
            )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(successful_tests)
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests_run": len(self.test_results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "performance_level": performance_level,
                "meets_1000_user_target": meets_1000_user_target
            },
            "aggregate_metrics": {
                "total_connections_tested": total_connections_tested,
                "total_messages_sent": total_messages_sent,
                "avg_p95_latency_ms": round(avg_p95_latency, 2),
                "avg_p99_latency_ms": round(avg_p99_latency, 2),
                "max_throughput_msg_per_sec": round(max_throughput, 2),
                "avg_error_rate_percent": round(avg_error_rate, 2),
                "peak_cpu_usage_percent": round(peak_cpu, 2),
                "peak_memory_usage_mb": round(peak_memory, 2)
            },
            "performance_grades": grade_counts,
            "target_validation": {
                "latency_target_100ms": avg_p95_latency <= 100,
                "throughput_target_1000_msg_sec": max_throughput >= 1000,
                "error_rate_target_1_percent": avg_error_rate <= 1.0,
                "concurrent_users_1000": meets_1000_user_target
            },
            "recommendations": recommendations,
            "detailed_results": successful_tests,
            "failed_tests": failed_tests
        }
    
    def _generate_recommendations(self, successful_tests: List[Dict]) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        # Analyze latency
        avg_p95_latency = sum(r['latency_metrics']['p95_ms'] for r in successful_tests) / len(successful_tests)
        if avg_p95_latency > 100:
            recommendations.append(
                f"Latency optimization needed: P95 latency is {avg_p95_latency:.1f}ms (target: <100ms). "
                "Consider optimizing message serialization, reducing network overhead, or implementing message batching."
            )
        
        # Analyze throughput
        max_throughput = max(r['message_metrics']['messages_per_second'] for r in successful_tests)
        if max_throughput < 1000:
            recommendations.append(
                f"Throughput optimization needed: Peak throughput is {max_throughput:.1f} msg/sec (target: >1000 msg/sec). "
                "Consider implementing connection pooling, message queuing, or horizontal scaling."
            )
        
        # Analyze error rates
        avg_error_rate = sum(r['error_metrics']['connection_error_rate'] for r in successful_tests) / len(successful_tests)
        if avg_error_rate > 1.0:
            recommendations.append(
                f"Error rate optimization needed: Average error rate is {avg_error_rate:.2f}% (target: <1%). "
                "Investigate connection stability, implement better error handling, and add connection retry logic."
            )
        
        # Analyze resource usage
        peak_cpu = max(r['resource_usage']['peak_cpu_usage'] for r in successful_tests)
        peak_memory = max(r['resource_usage']['peak_memory_mb'] for r in successful_tests)
        
        if peak_cpu > 80:
            recommendations.append(
                f"CPU optimization needed: Peak CPU usage is {peak_cpu:.1f}% (recommended: <80%). "
                "Consider optimizing CPU-intensive operations, implementing async processing, or scaling horizontally."
            )
        
        if peak_memory > 2000:
            recommendations.append(
                f"Memory optimization needed: Peak memory usage is {peak_memory:.1f}MB (recommended: <2GB). "
                "Consider implementing memory pooling, optimizing data structures, or adding garbage collection tuning."
            )
        
        # Check for 1000+ user capability
        high_load_tests = [r for r in successful_tests if r['config']['max_connections'] >= 1000]
        if not high_load_tests or not any(r['test_results']['overall_success'] for r in high_load_tests):
            recommendations.append(
                "1000+ concurrent user target not met. Consider implementing advanced optimizations: "
                "connection pooling, load balancing, message queuing, and horizontal scaling."
            )
        
        if not recommendations:
            recommendations.append("Excellent performance! All targets met. Consider stress testing with even higher loads.")
        
        return recommendations


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WebSocket Performance Test Suite")
    parser.add_argument("--host", default="localhost", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--output", default=None, help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create test suite
    test_suite = PerformanceTestSuite(args.host, args.port)
    
    try:
        # Run tests
        report = await test_suite.run_all_tests(quick_mode=args.quick)
        
        # Save results
        output_file = args.output or f"websocket_performance_report_{int(time.time())}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "="*100)
        print("WEBSOCKET PERFORMANCE TEST SUITE RESULTS")
        print("="*100)
        
        if report.get('status') == 'completed':
            summary = report['summary']
            metrics = report['aggregate_metrics']
            validation = report['target_validation']
            
            print(f"Tests Run: {summary['successful_tests']}/{summary['total_tests_run']} successful")
            print(f"Performance Level: {summary['performance_level']}")
            print(f"1000+ User Target: {'✅ MET' if summary['meets_1000_user_target'] else '❌ NOT MET'}")
            print()
            print("PERFORMANCE METRICS:")
            print(f"  Average P95 Latency: {metrics['avg_p95_latency_ms']:.1f}ms")
            print(f"  Max Throughput: {metrics['max_throughput_msg_per_sec']:.1f} msg/sec")
            print(f"  Average Error Rate: {metrics['avg_error_rate_percent']:.2f}%")
            print(f"  Peak CPU Usage: {metrics['peak_cpu_usage_percent']:.1f}%")
            print(f"  Peak Memory Usage: {metrics['peak_memory_usage_mb']:.1f}MB")
            print()
            print("TARGET VALIDATION:")
            print(f"  Latency <100ms: {'✅' if validation['latency_target_100ms'] else '❌'}")
            print(f"  Throughput >1000 msg/sec: {'✅' if validation['throughput_target_1000_msg_sec'] else '❌'}")
            print(f"  Error Rate <1%: {'✅' if validation['error_rate_target_1_percent'] else '❌'}")
            print(f"  1000+ Concurrent Users: {'✅' if validation['concurrent_users_1000'] else '❌'}")
            print()
            print("RECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        else:
            print(f"Test suite failed: {report.get('message', 'Unknown error')}")
        
        print("="*100)
        print(f"Detailed results saved to: {output_file}")
        
        # Exit with appropriate code
        if report.get('status') == 'completed' and report['summary']['meets_1000_user_target']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
            
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())