#!/usr/bin/env python3
"""
Protocol OMNI v16.2.2 - Agent Connection Test Script

Phase 3: Agent Orchestration Integration Test
Tests the Cognitive Trinity routing: DeepSeek (Oracle) → Qwen (Executor)

Usage:
    python scripts/test_agent_connection.py --host 192.168.3.10
"""

import argparse
import json
import sys
import time
from typing import Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


class TrilogyTester:
    def __init__(self, host: str, timeout: int = 60):
        self.oracle_url = f"http://{host}:8000/v1/chat/completions"
        self.executor_url = f"http://{host}:8002/v1/chat/completions"
        self.orchestrator_url = f"http://{host}:8080/v1/chat/completions"
        self.phoenix_url = f"http://{host}:6006/health"
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _chat_request(self, prompt: str, model: str = "auto") -> dict:
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": False,
        }

    def check_health(self, name: str, url: str) -> bool:
        try:
            health_url = url.replace("/v1/chat/completions", "/health")
            resp = self.client.get(health_url, timeout=10)
            if resp.status_code == 200:
                print(f"  [OK] {name}: healthy")
                return True
            print(f"  [WARN] {name}: status {resp.status_code}")
            return False
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            return False

    def test_oracle_planning(self, task: str) -> Optional[dict]:
        """Send planning task to DeepSeek (Oracle)."""
        print(f"\n[1/3] Sending COMPLEX task to Oracle (DeepSeek-V3.2)...")
        
        prompt = f"""You are a planning agent. Analyze this task and return a JSON execution plan.

Task: {task}

Return ONLY a valid JSON object with this structure:
{{
    "plan_id": "unique-id",
    "steps": [
        {{"step": 1, "action": "description", "tool": "tool_name"}},
        {{"step": 2, "action": "description", "tool": "tool_name"}}
    ],
    "complexity": "COMPLEX",
    "estimated_tokens": 500
}}"""
        
        try:
            start = time.perf_counter()
            resp = self.client.post(
                self.oracle_url,
                json=self._chat_request(prompt),
                timeout=300,
            )
            latency = (time.perf_counter() - start) * 1000
            
            if resp.status_code != 200:
                print(f"  [FAIL] Oracle returned {resp.status_code}: {resp.text[:200]}")
                return None
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"  [OK] Oracle responded in {latency:.0f}ms")
            print(f"  Response preview: {content[:150]}...")
            
            try:
                plan = json.loads(content.strip().replace("```json", "").replace("```", ""))
                print(f"  [OK] Valid JSON plan with {len(plan.get('steps', []))} steps")
                return plan
            except json.JSONDecodeError:
                print(f"  [WARN] Response is not valid JSON, returning raw text")
                return {"raw": content, "steps": [{"step": 1, "action": content}]}
                
        except Exception as e:
            print(f"  [FAIL] Oracle error: {e}")
            return None

    def test_executor_coding(self, plan: dict) -> Optional[str]:
        """Send code generation task to Qwen (Executor)."""
        print(f"\n[2/3] Sending ROUTINE coding task to Executor (Qwen)...")
        
        steps = plan.get("steps", [{"action": "Write a hello world function"}])
        first_step = steps[0] if steps else {"action": "Generate code"}
        
        prompt = f"""You are a coding executor. Complete this step from an execution plan:

Step: {first_step.get('action', first_step)}

Return ONLY the code implementation, no explanation."""
        
        try:
            start = time.perf_counter()
            resp = self.client.post(
                self.executor_url,
                json=self._chat_request(prompt),
                timeout=60,
            )
            latency = (time.perf_counter() - start) * 1000
            
            if resp.status_code != 200:
                print(f"  [FAIL] Executor returned {resp.status_code}: {resp.text[:200]}")
                return None
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"  [OK] Executor responded in {latency:.0f}ms")
            print(f"  Code preview: {content[:150]}...")
            
            return content
            
        except Exception as e:
            print(f"  [FAIL] Executor error: {e}")
            return None

    def test_orchestrator_routing(self) -> bool:
        """Test the Agent Orchestrator auto-routing."""
        print(f"\n[3/3] Testing Agent Orchestrator routing...")
        
        test_cases = [
            ("Hello!", "TRIVIAL", "qwen"),
            ("Write a Python function to sort a list", "ROUTINE", "qwen"),
            ("Deploy the CUDA kernel to GPU and trace execution", "COMPLEX", "deepseek"),
        ]
        
        passed = 0
        for prompt, expected_complexity, expected_model in test_cases:
            try:
                resp = self.client.post(
                    self.orchestrator_url,
                    json=self._chat_request(prompt),
                    timeout=300,
                )
                
                if resp.status_code != 200:
                    print(f"    [FAIL] '{prompt[:30]}...' → {resp.status_code}")
                    continue
                
                data = resp.json()
                model = data.get("model", "unknown")
                reason = data.get("routing_reason", "")
                
                matched = expected_model in model.lower()
                status = "[OK]" if matched else "[WARN]"
                print(f"    {status} '{prompt[:30]}...' → {model}")
                
                if matched:
                    passed += 1
                    
            except Exception as e:
                print(f"    [FAIL] '{prompt[:30]}...' → {e}")
        
        print(f"  Routing tests: {passed}/{len(test_cases)} passed")
        return passed == len(test_cases)

    def run_full_test(self, task: str) -> bool:
        print("=" * 60)
        print("Protocol OMNI v16.2.2 - Cognitive Trinity Integration Test")
        print("=" * 60)
        
        print("\n[0/3] Health Check...")
        health_ok = all([
            self.check_health("Oracle (DeepSeek)", self.oracle_url),
            self.check_health("Executor (Qwen)", self.executor_url),
            self.check_health("Orchestrator", self.orchestrator_url),
        ])
        
        try:
            resp = self.client.get(self.phoenix_url, timeout=5)
            print(f"  [OK] Observer (Phoenix): healthy")
        except Exception:
            print(f"  [WARN] Observer (Phoenix): not responding (optional)")
        
        if not health_ok:
            print("\n[ABORT] Some services are down. Fix before continuing.")
            return False
        
        plan = self.test_oracle_planning(task)
        if not plan:
            return False
        
        code = self.test_executor_coding(plan)
        if not code:
            return False
        
        routing_ok = self.test_orchestrator_routing()
        
        print("\n" + "=" * 60)
        print("RESULT: " + ("PASS" if routing_ok else "PARTIAL"))
        print("=" * 60)
        
        return routing_ok


def main():
    parser = argparse.ArgumentParser(description="Test Cognitive Trinity connectivity")
    parser.add_argument("--host", default="192.168.3.10", help="Host IP (default: 192.168.3.10)")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    parser.add_argument("--task", default="Create a REST API endpoint for user authentication",
                        help="Task to send to Oracle for planning")
    args = parser.parse_args()
    
    tester = TrilogyTester(host=args.host, timeout=args.timeout)
    success = tester.run_full_test(task=args.task)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
