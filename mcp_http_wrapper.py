#!/usr/bin/env python3
"""
HTTP обертка для MCP сервера Reddit
Позволяет использовать MCP сервер через HTTP API
"""

import asyncio
import json
import os
import subprocess
import sys
from flask import Flask, jsonify, request
import threading
import time

app = Flask(__name__)

class MCPClient:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        
    def start_mcp_server(self):
        """Запускает MCP сервер как подпроцесс"""
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "mcp_server_reddit"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            return True
        except Exception as e:
            print(f"Ошибка запуска MCP сервера: {e}")
            return False
    
    def send_request(self, method, params=None):
        """Отправляет запрос в MCP сервер"""
        if not self.process or self.process.poll() is not None:
            if not self.start_mcp_server():
                return {"error": "Не удается запустить MCP сервер"}
        
        with self.lock:
            try:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params or {}
                }
                
                request_json = json.dumps(request_data) + "\n"
                self.process.stdin.write(request_json)
                self.process.stdin.flush()
                
                # Читаем ответ
                response_line = self.process.stdout.readline()
                if response_line:
                    return json.loads(response_line.strip())
                else:
                    return {"error": "Нет ответа от MCP сервера"}
                    
            except Exception as e:
                return {"error": f"Ошибка связи с MCP сервером: {str(e)}"}

# Глобальный экземпляр клиента
mcp_client = MCPClient()

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return jsonify({"status": "ok", "service": "MCP Reddit HTTP Wrapper"})

@app.route('/tools')
def list_tools():
    """Получить список доступных инструментов"""
    response = mcp_client.send_request("tools/list")
    return jsonify(response)

@app.route('/reddit/frontpage')
def get_frontpage():
    """Получить посты с главной страницы Reddit"""
    limit = request.args.get('limit', 10, type=int)
    response = mcp_client.send_request("tools/call", {
        "name": "get_frontpage_posts",
        "arguments": {"limit": limit}
    })
    return jsonify(response)

@app.route('/reddit/subreddit/<subreddit>')
def get_subreddit(subreddit):
    """Получить информацию о сабреддите"""
    response = mcp_client.send_request("tools/call", {
        "name": "get_subreddit_info",
        "arguments": {"subreddit": subreddit}
    })
    return jsonify(response)

@app.route('/reddit/subreddit/<subreddit>/hot')
def get_subreddit_hot(subreddit):
    """Получить горячие посты сабреддита"""
    limit = request.args.get('limit', 10, type=int)
    response = mcp_client.send_request("tools/call", {
        "name": "get_subreddit_hot_posts",
        "arguments": {"subreddit": subreddit, "limit": limit}
    })
    return jsonify(response)

@app.route('/reddit/post/<post_id>')
def get_post(post_id):
    """Получить детали поста"""
    response = mcp_client.send_request("tools/call", {
        "name": "get_post_details",
        "arguments": {"post_id": post_id}
    })
    return jsonify(response)

@app.route('/reddit/post/<post_id>/comments')
def get_post_comments(post_id):
    """Получить комментарии к посту"""
    limit = request.args.get('limit', 20, type=int)
    response = mcp_client.send_request("tools/call", {
        "name": "get_post_comments",
        "arguments": {"post_id": post_id, "limit": limit}
    })
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Запуск HTTP обертки для MCP Reddit сервера на порту {port}")
    
    # Тестируем подключение к MCP серверу
    if mcp_client.start_mcp_server():
        print("MCP сервер успешно запущен")
    else:
        print("Предупреждение: не удалось запустить MCP сервер")
    
    app.run(host='0.0.0.0', port=port, debug=False)
