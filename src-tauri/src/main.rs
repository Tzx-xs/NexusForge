#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// NexusForge 桌面端入口
// 职责：启动 PyInstaller 打包的后端 exe → 等健康检查通过 → 窗口加载 127.0.0.1:8005
// 关闭窗口时 kill 后端进程

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Manager, WindowEvent};

/// 持有后端子进程，退出时 kill
struct BackendState(Mutex<Option<Child>>);

fn main() {
    tauri::Builder::default()
        .manage(BackendState(Mutex::new(None)))
        .setup(|app| {
            // 定位后端 exe（resources/nexusforge-backend/nexusforge-backend.exe）
            let resource_path = app.path().resource_dir()?;
            let backend_dir = resource_path.join("nexusforge-backend");
            let backend_exe = backend_dir.join("nexusforge-backend.exe");

            // 数据目录重定向到 %APPDATA%/com.nexusforge.desktop/data
            let data_dir = app.path().app_data_dir()?;
            let data_dir = data_dir.join("data");
            std::fs::create_dir_all(&data_dir)?;

            let port = 8005;
            let child = Command::new(&backend_exe)
                .arg(port.to_string())
                .current_dir(&backend_dir)
                .env(
                    "NEXUSFORGE_PROD_DATA_DIR",
                    &*data_dir.to_string_lossy(),
                )
                .env("APP_ENV", "production")
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()?;

            // 存到 state 以便退出时 kill
            let state = app.state::<BackendState>();
            *state.0.lock().unwrap() = Some(child);

            // 轮询健康检查（最多等 30 秒）
            let start = Instant::now();
            loop {
                if start.elapsed() > Duration::from_secs(30) {
                    eprintln!("[NexusForge] 后端 30 秒内未启动，窗口可能显示空白");
                    break;
                }
                if std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok() {
                    break;
                }
                std::thread::sleep(Duration::from_millis(500));
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            // 关闭窗口时 kill 后端
            if let WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<BackendState>();
                let mut guard = state.0.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running NexusForge");
}
