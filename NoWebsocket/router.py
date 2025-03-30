# websocket_server/router.py
import re
import importlib
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Route:
    """路由条目封装类"""
    def __init__(self, pattern, handler, param_types, raw_path):
        self.pattern = re.compile(pattern)
        self.handler = handler
        self.param_types = param_types
        self.raw_path = raw_path

class WebSocketRouter:
    """路由管理器（支持冲突检测）"""
    def __init__(self):
        self.routes = []
        self._registered_paths = set()

    def add_route(self, path, handler):
        if path in self._registered_paths:
            logger.warning(f"路由冲突: 路径 '{path}' 已存在，本次注册将被忽略")
            return False
        pattern_str, param_types = self._parse_path(path)
        self.routes.append(Route(pattern_str, handler, param_types, path))
        self._registered_paths.add(path)
        logger.info(f"路由注册成功: {path} -> {handler.__name__}")
        return True

    def path_exists(self, path):
        return path in self._registered_paths

    def _parse_path(self, path):
        param_types = {}
        def replace_token(match):
            name = match.group(1)
            type_hint = match.group(2) or 'str'
            param_types[name] = type_hint
            return {
                'int': r'(?P<{}>\d+)'.format(name),
                'str': r'(?P<{}>[^/]+)'.format(name)
            }.get(type_hint, r'(?P<{}>{})'.format(name, type_hint))
        pattern_str = re.sub(r'\{(\w+)(?::([^}]+))?\}', replace_token, path)
        return f'^{pattern_str}$', param_types

    def match(self, request_path):
        for route in self.routes:
            match = route.pattern.match(request_path)
            if match:
                params = self._cast_params(match.groupdict(), route.param_types)
                return route.handler, params
        return None, None

    @staticmethod
    def _cast_params(params, types):
        result = {}
        for name, value in params.items():
            type_hint = types.get(name, 'str')
            try:
                result[name] = int(value) if type_hint == 'int' else value
            except ValueError:
                pass
        return result

class Blueprint:
    """路由蓝图（记录模块路径）"""
    def __init__(self, prefix=''):
        self.prefix = prefix.rstrip('/')
        self._routes = []
        self.module_path = None  # 新增：记录模块导入路径（如 blueprints.chat_bp）

    def route(self, path):
        def decorator(handler):
            full_path = f"{self.prefix}{path}"
            self._routes.append((full_path, handler))
            return handler
        return decorator

    def register(self, router):
        conflict_detected = False
        for path, _ in self._routes:
            if router.path_exists(path):
                # 打印模块路径而非文件路径
                logger.warning(
                    f"蓝图路由冲突: 路径 '{path}' 已存在，跳过模块 '{self.module_path}' 的注册"
                )
                conflict_detected = True
                break
        if conflict_detected:
            return False
        for path, handler in self._routes:
            router.add_route(path, handler)
        return True

    @classmethod
    def auto_discover(cls, router, package='blueprints'):
        try:
            package_module = importlib.import_module(package)
        except ImportError:
            logger.warning(f"蓝图包 '{package}' 未找到")
            return
        package_dir = Path(package_module.__file__).parent
        for root, _, files in os.walk(package_dir):
            rel_path = Path(root).relative_to(package_dir)
            module_prefix = f"{package}.{'.'.join(rel_path.parts)}" if rel_path.parts else package
            for file in files:
                if not (file.endswith('_bp.py') or file.endswith('Bp.py')) or file == '__init__.py':
                    continue
                # 构造模块名（如 blueprints.chat_bp）
                module_name = f"{module_prefix}.{file[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                except Exception as e:
                    logger.error(f"导入模块失败: {module_name} - {str(e)}")
                    continue
                # 为蓝图实例设置模块路径
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if isinstance(obj, Blueprint):
                        obj.module_path = module_name  # 记录模块导入路径
                        success = obj.register(router)
                        if success:
                            logger.info(f"自动注册蓝图: {module_name} -> {obj.prefix}")