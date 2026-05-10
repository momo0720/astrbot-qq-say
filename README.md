# astrbot-qq-say

一个用于生成仿 QQ 合并转发聊天记录的 AstrBot 插件。

## 特性

- 支持多发言人合并转发聊天生成。
- 支持可配置分隔符、群白名单、私聊开关和保护账号。

## 安装

1. 克隆或下载本仓库。
2. 将 `qq_say` 目录复制到 AstrBot 的插件目录中。
3. 在 AstrBot 插件配置页填写所需配置。
4. 重启 AstrBot 或重载插件。

## 使用

- 主命令：`/qq说`
- 更多命令示例：见 `qq_say/README.md`

## 仓库结构

- `qq_say/main.py`
- `qq_say/_conf_schema.json`
- `qq_say/metadata.yaml`
- `qq_say/README.md`

## 说明

- 已将本地敏感 API 地址和 Key 替换为占位内容（如适用）。
- 不包含运行环境中的本地配置文件。
