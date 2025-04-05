from setuptools import setup, find_packages

setup(
    name="NoWebsocket",          # 包名称（PyPI 唯一标识）
    version="2.2.1",            # 版本号
    author="dzy",
    author_email="1129881228@qq.com",
    description="一个面向对象的Python WebSocket服务端框架，支持零配置多文件路由管理，实现高效、模块化的实时通信开发。",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dzy-china/NoWebsocket",
    packages=find_packages(),
    install_requires=[ ],# 依赖项（可选）
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",    # Python 版本要求
)