#!/usr/bin/env python3
"""
Local Inference Backends for Trinity-SWE
Supports multiple local inference options to replace API calls
"""

import json
import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class InferenceConfig:
    backend: str  # 'ollama', 'vllm', 'tgi', 'llamacpp'
    model_name: str
    base_url: str
    max_tokens: int = 4000
    temperature: float = 0.1
    extra_params: Dict[str, Any] = None

class LocalInferenceBackend(ABC):
    def __init__(self, config: InferenceConfig):
        self.config = config
        
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate response from local model"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is available"""
        pass

class OllamaBackend(LocalInferenceBackend):
    """Ollama local inference backend"""
    
    async def generate(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": self.config.max_tokens,
                    "temperature": self.config.temperature
                }
            }
            
            try:
                async with session.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
            except Exception as e:
                logging.error(f"Ollama generation error: {e}")
                return ""
    
    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/api/tags") as response:
                    return response.status == 200
        except:
            return False

class VLLMBackend(LocalInferenceBackend):
    """vLLM OpenAI-compatible API backend"""
    
    async def generate(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": False
            }
            
            try:
                async with session.post(
                    f"{self.config.base_url}/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        raise Exception(f"vLLM API error: {response.status}")
            except Exception as e:
                logging.error(f"vLLM generation error: {e}")
                return ""
    
    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/v1/models") as response:
                    return response.status == 200
        except:
            return False

class TGIBackend(LocalInferenceBackend):
    """Text Generation Inference backend"""
    
    async def generate(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "do_sample": True,
                    "return_full_text": False
                }
            }
            
            try:
                async with session.post(
                    f"{self.config.base_url}/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("generated_text", "")
                    else:
                        raise Exception(f"TGI API error: {response.status}")
            except Exception as e:
                logging.error(f"TGI generation error: {e}")
                return ""
    
    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/health") as response:
                    return response.status == 200
        except:
            return False

class LlamaCppBackend(LocalInferenceBackend):
    """llama.cpp server backend"""
    
    async def generate(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "prompt": prompt,
                "n_predict": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": False
            }
            
            try:
                async with session.post(
                    f"{self.config.base_url}/completion",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("content", "")
                    else:
                        raise Exception(f"llama.cpp API error: {response.status}")
            except Exception as e:
                logging.error(f"llama.cpp generation error: {e}")
                return ""
    
    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/health") as response:
                    return response.status == 200
        except:
            return False

class LocalInferenceManager:
    """Manages multiple local inference backends with fallback"""
    
    def __init__(self, configs: List[InferenceConfig]):
        self.backends = []
        for config in configs:
            backend = self._create_backend(config)
            if backend:
                self.backends.append(backend)
        
        if not self.backends:
            raise ValueError("No valid inference backends configured")
    
    def _create_backend(self, config: InferenceConfig) -> Optional[LocalInferenceBackend]:
        """Factory method to create backend instances"""
        backend_map = {
            'ollama': OllamaBackend,
            'vllm': VLLMBackend,
            'tgi': TGIBackend,
            'llamacpp': LlamaCppBackend
        }
        
        backend_class = backend_map.get(config.backend)
        if backend_class:
            return backend_class(config)
        else:
            logging.warning(f"Unknown backend: {config.backend}")
            return None
    
    async def generate(self, prompt: str) -> str:
        """Try backends in order until one succeeds"""
        for i, backend in enumerate(self.backends):
            try:
                if await backend.health_check():
                    result = await backend.generate(prompt)
                    if result:
                        return result
                    else:
                        logging.warning(f"Backend {backend.config.backend} returned empty response")
                else:
                    logging.warning(f"Backend {backend.config.backend} health check failed")
            except Exception as e:
                logging.error(f"Backend {backend.config.backend} failed: {e}")
                continue
        
        # All backends failed
        raise Exception("All local inference backends failed")
    
    async def get_available_backends(self) -> List[str]:
        """Get list of currently available backends"""
        available = []
        for backend in self.backends:
            if await backend.health_check():
                available.append(backend.config.backend)
        return available

# Predefined configurations for popular setups
PRESET_CONFIGS = {
    "ollama_qwen": InferenceConfig(
        backend="ollama",
        model_name="qwen2.5-coder:latest",  # Available model
        base_url="http://localhost:11434"
    ),
    
    "ollama_codellama": InferenceConfig(
        backend="ollama", 
        model_name="codellama:34b",
        base_url="http://localhost:11434"
    ),
    
    "vllm_qwen": InferenceConfig(
        backend="vllm",
        model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
        base_url="http://localhost:8000"
    ),
    
    "tgi_qwen": InferenceConfig(
        backend="tgi",
        model_name="Qwen/Qwen2.5-Coder-32B-Instruct", 
        base_url="http://localhost:3000"
    )
}

async def test_local_setup():
    """Test function to check what's available locally"""
    print("🔍 Testing local inference setups...")
    
    for name, config in PRESET_CONFIGS.items():
        backend = None
        if config.backend == "ollama":
            backend = OllamaBackend(config)
        elif config.backend == "vllm":
            backend = VLLMBackend(config)
        elif config.backend == "tgi":
            backend = TGIBackend(config)
        
        if backend:
            available = await backend.health_check()
            status = "✅ Available" if available else "❌ Not available"
            print(f"{name}: {status}")
            
            if available:
                try:
                    test_response = await backend.generate("Hello, how are you?")
                    print(f"  Test response: {test_response[:50]}...")
                except Exception as e:
                    print(f"  Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_local_setup())