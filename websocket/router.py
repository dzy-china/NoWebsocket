# websocket/router.py
import re
import importlib.util
import os
from pathlib import Path


class WebSocketRouter:
    def __init__(self):
        self.routes = []

    def add_route(self, path, handler):
        if not path.startswith('/'):
            raise ValueError("Path must start with '/'")
        pattern_str, param_types = self._parse_path(path)
        compiled = re.compile(pattern_str)
        self.routes.append({
            'pattern': compiled,
            'param_types': param_types,
            'handler': handler
        })

    def _parse_path(self, path):
        param_types = {}

        def replace(match):
            name = match.group(1)
            type_hint = match.group(2) or 'str'
            param_types[name] = type_hint
            regex = {
                'int': r'\d+',
                'str': r'[^/]+'
            }.get(type_hint, type_hint)
            return f'(?P<{name}>{regex})'

        pattern_str = re.sub(r'\{(\w+)(?::([^}]+))?\}', replace, path)
        return f'^{pattern_str}$', param_types

    def match(self, request_path):
        for route in self.routes:
            m = route['pattern'].match(request_path)
            if m:
                params = {}
                for name, value in m.groupdict().items():
                    type_hint = route['param_types'].get(name, 'str')
                    if type_hint == 'int':
                        try:
                            params[name] = int(value)
                        except ValueError:
                            return None, None
                    else:
                        params[name] = value
                return route['handler'], params
        return None, None


class Blueprint:
    """路由蓝图，支持自动注册"""

    def __init__(self, prefix=''):
        self._routes = []
        self.prefix = prefix.rstrip('/')

    def route(self, path):
        """路由装饰器工厂"""

        def decorator(handler):
            full_path = f"{self.prefix}{path}"
            self._routes.append((full_path, handler))
            return handler

        return decorator

    def register(self, router):
        """将蓝图中的路由注册到路由器"""
        for path, handler in self._routes:
            router.add_route(path, handler)

    @classmethod
    def auto_register(cls, router, package_path='blueprints', bp_suffix='_bp'):
        """
        自动注册蓝图
        :param router: WebSocketRouter实例
        :param package_path: 蓝图包路径，默认为'blueprints'
        :param bp_suffix: 蓝图实例后缀，默认为'_bp'
        """
        package_dir = Path(__file__).parent.parent / package_path

        if not package_dir.exists():
            raise ValueError(f"Blueprint directory {package_dir} not found")

        for root, _, files in os.walk(package_dir):
            relative_path = Path(root).relative_to(package_dir.parent)
            package_prefix = str(relative_path).replace(os.sep, '.')

            for file in files:
                if not file.endswith('.py') or file == '__init__.py':
                    continue

                module_name = f"{package_prefix}.{file[:-3]}"
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        os.path.join(root, file)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr in dir(module):
                        obj = getattr(module, attr)
                        if isinstance(obj, Blueprint) and attr.endswith(bp_suffix):
                            obj.register(router)
                            print(f"Auto-registered blueprint: {module_name}.{attr}")

                except Exception as e:
                    print(f"Failed to load {file}: {str(e)}")