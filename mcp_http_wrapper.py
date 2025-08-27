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
                }

                if params:                                                                                                                                                                                                         │
                   request_data['params'] = params
                
                request_json = json.dumps(request_data) + "\n"
                print(f"DEBUG: Отправляю в MCP: {request_json.strip()}", flush=True) # ОТЛАДКА
                self.process.stdin.write(request_json)
                self.process.stdin.flush()
                
                # Читаем ответ
                response_line = self.process.stdout.readline()
                print(f"DEBUG: Получено от MCP: {response_line.strip()}", flush=True) # ОТЛАДКА
                if response_line:
                    return json.loads(response_line.strip())
                else:
                    return {"error": "Нет ответа от MCP сервера"}
                    
            except Exception as e:
                print(f"DEBUG: Исключение в send_request: {e}", flush=True) # ОТЛАДКА
                return {"error": f"Ошибка связи с MCP сервером: {str(e)}"}

# Глобальный экземпляр клиента
mcp_client = MCPClient()

@app.route('/')
def index():
    """Главная страница с документацией API"""
    return """
    <h1>MCP Reddit API Server</h1>
    <p>HTTP обертка для MCP сервера Reddit</p>
    
    <h2>Доступные endpoints:</h2>
    <ul>
        <li><a href="/health">/health</a> - Проверка здоровья сервиса</li>
        <li><a href="/tools">/tools</a> - Список доступных инструментов</li>
        <li><a href="/reddit/frontpage?limit=5">/reddit/frontpage?limit=5</a> - Главная страница Reddit</li>
        <li>/reddit/subreddit/&lt;subreddit&gt; - Информация о сабреддите</li>
        <li>/reddit/subreddit/&lt;subreddit&gt;/hot?limit=10 - Горячие посты сабреддита</li>
        <li>/reddit/post/&lt;post_id&gt; - Детали поста</li>
        <li>/reddit/post/&lt;post_id&gt;/comments - Комментарии к посту</li>
    </ul>
    
    <h2>Примеры:</h2>
    <ul>
        <li><a href="/reddit/subreddit/python">/reddit/subreddit/python</a></li>
        <li><a href="/reddit/subreddit/programming/hot?limit=3">/reddit/subreddit/programming/hot?limit=3</a></li>
    </ul>
    """

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return jsonify({"status": "ok", "service": "MCP Reddit HTTP Wrapper"})

@app.route('/tools')
def list_tools():
    """Получить список доступных инструментов"""
    response = mcp_client.send_request("tools/list")
    return jsonify(response)

@app.route('/api/reddit/frontpage', methods=['GET', 'POST'])
def api_frontpage():
    """Получить посты с главной страницы Reddit (GET/POST)"""
    if request.method == 'POST':
        data = request.get_json() or {}
        limit = data.get('limit', 10)
    else:
        limit = request.args.get('limit', 10, type=int)
        
    response = mcp_client.send_request("tools/call", {
        "name": "get_frontpage_posts",
        "arguments": {"limit": limit}
    })
    return jsonify(response)

@app.route('/api/reddit/subreddit', methods=['POST'])
def api_subreddit_info():
    """Получить информацию о сабреддите через POST"""
    data = request.get_json()
    if not data or 'subreddit_name' not in data:
        return jsonify({"error": "Требуется параметр 'subreddit_name' в JSON"}), 400
    
    response = mcp_client.send_request("tools/call", {
        "name": "get_subreddit_info",
        "arguments": {"subreddit_name": data['subreddit_name']}
    })
    return jsonify(response)

@app.route('/api/reddit/subreddit/hot', methods=['POST'])
def api_subreddit_hot():
    """Получить горячие посты сабреддита через POST"""
    data = request.get_json()
    if not data or 'subreddit_name' not in data:
        return jsonify({"error": "Требуется параметр 'subreddit_name' в JSON"}), 400
    
    limit = data.get('limit', 10)
    response = mcp_client.send_request("tools/call", {
        "name": "get_subreddit_hot_posts",
        "arguments": {"subreddit_name": data['subreddit_name'], "limit": limit}
    })
    return jsonify(response)

@app.route('/api/reddit/post', methods=['POST'])
def api_post_details():
    """Получить детали поста через POST"""
    data = request.get_json()
    if not data or 'post_id' not in data:
        return jsonify({"error": "Требуется параметр 'post_id' в JSON"}), 400
    
    response = mcp_client.send_request("tools/call", {
        "name": "get_post_content",
        "arguments": {"post_id": data['post_id']}
    })
    return jsonify(response)

@app.route('/api/reddit/comments', methods=['POST'])
def api_post_comments():
    """Получить комментарии к посту через POST"""
    data = request.get_json()
    if not data or 'post_id' not in data:
        return jsonify({"error": "Требуется параметр 'post_id' в JSON"}), 400
    
    limit = data.get('limit', 20)
    response = mcp_client.send_request("tools/call", {
        "name": "get_post_comments",
        "arguments": {"post_id": data['post_id'], "limit": limit}
    })
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
        "arguments": {"subreddit_name": subreddit}
    })
    return jsonify(response)

@app.route('/reddit/subreddit/<subreddit>/hot')
def get_subreddit_hot(subreddit):
    """Получить горячие посты сабреддита"""
    limit = request.args.get('limit', 10, type=int)
    response = mcp_client.send_request("tools/call", {
        "name": "get_subreddit_hot_posts",
        "arguments": {"subreddit_name": subreddit, "limit": limit}
    })
    return jsonify(response)

@app.route('/reddit/post/<post_id>')
def get_post(post_id):
    """Получить детали поста"""
    response = mcp_client.send_request("tools/call", {
        "name": "get_post_content",
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

@app.route('/api/reddit/search_subreddits', methods=['POST'])
def api_search_subreddits():
    """Поиск сабреддитов по запросу и фильтрам подписчиков"""
    data = request.get_json() or {}
    if 'query' not in data:
        return jsonify({"error": "Требуется параметр 'query' в JSON"}), 400
    args = {
        "query": data['query'],
        "limit": data.get('limit', 10)
    }
    if 'min_subscribers' in data:
        args['min_subscribers'] = data['min_subscribers']
    if 'max_subscribers' in data:
        args['max_subscribers'] = data['max_subscribers']
    response = mcp_client.send_request("tools/call", {
        "name": "search_subreddits",
        "arguments": args
    })
    return jsonify(response)

@app.route('/api/reddit/find_unpopular_subreddits', methods=['POST'])
def api_find_unpopular_subreddits():
    """Найти непопулярные сабреддиты по порогу подписчиков и опциональному запросу"""
    data = request.get_json() or {}
    try:
        args = {
            "query": data.get('query', ''),
            "max_subscribers": int(data.get('max_subscribers', 50000)),
            "limit": int(data.get('limit', 10))
        }
    except (ValueError, TypeError):
        return jsonify({"error": "Параметры 'limit' и 'max_subscribers' должны быть числами"}), 400
        
    response = mcp_client.send_request("tools/call", {
        "name": "find_unpopular_subreddits",
        "arguments": args
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
