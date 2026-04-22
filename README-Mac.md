# Dacheng Live Whiteboard

这是一个带**白板界面 + 本地 JSON 持久化**的小日常规划板。

## 在 Mac 上怎么打开
1. 下载并解压这个文件夹
2. 打开 Terminal，进入这个文件夹
3. 双击 `open-whiteboard.command`
4. 浏览器会自动打开白板

如果双击 `.command` 第一次被 macOS 拦住：
- 右键 `open-whiteboard.command`
- 选择“打开”
- 再确认一次

## 数据保存方式
- 示例仓库内附带的是**脱敏 demo 数据**
- 运行后新的白板状态会保存到 `state_backups/`

## 文件说明
- `index.html`：白板 UI
- `serve_spa.py`：本地小服务，负责页面和 `/api/state`
- `open-whiteboard.command`：Mac 一键启动脚本

## 适合的使用方式
- 平时把这个网页固定在浏览器标签页里
- 或者单独开一个窗口，当成桌面小白板使用
