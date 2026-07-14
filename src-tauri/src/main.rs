#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// NexusForge 桌面端入口
// 职责：启动 PyInstaller 打包的后端 exe → 窗口加载 127.0.0.1:8005
// 后端 stdout/stderr 写到日志文件便于排查；关闭窗口时 kill 后端

use std::fs::OpenOptions;
use std::io::Write;
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
            let app_data_dir = app.path().app_data_dir()?;
            let data_dir = app_data_dir.join("data");
            std::fs::create_dir_all(&data_dir)?;

            // 日志文件：后端 stdout/stderr 重定向到这里
            let log_dir = app_data_dir.join("logs");
            std::fs::create_dir_all(&log_dir)?;
            let log_file = log_dir.join("backend.log");

            // 写入启动头信息
            if let Ok(mut log_handle) = OpenOptions::new()
                .create(true)
                .write(true)
                .truncate(true)
                .open(&log_file)
            {
                let _ = writeln!(
                    log_handle,
                    "[NexusForge Desktop] 启动后端: {}",
                    backend_exe.display()
                );
                let _ = writeln!(
                    log_handle,
                    "[NexusForge Desktop] 数据目录: {}",
                    data_dir.display()
                );
                let _ = writeln!(
                    log_handle,
                    "[NexusForge Desktop] 日志文件: {}",
                    log_file.display()
                );
            }

            let port = 8005;

            // 打开日志文件用于后端 stdout/stderr
            let stdout_handle = OpenOptions::new()
                .create(true)
                .write(true)
                .append(true)
                .open(&log_file)?;
            let stderr_handle = OpenOptions::new()
                .create(true)
                .write(true)
                .append(true)
                .open(&log_file)?;

            let child = Command::new(&backend_exe)
                .arg(port.to_string())
                .current_dir(&backend_dir)
                .env(
                    "NEXUSFORGE_PROD_DATA_DIR",
                    data_dir.to_string_lossy().as_ref(),
                )
                .env("APP_ENV", "production")
                .stdout(Stdio::from(stdout_handle))
                .stderr(Stdio::from(stderr_handle))
                .stdin(Stdio::null())
                .spawn();

            let child = match child {
                Ok(c) => c,
                Err(e) => {
                    if let Ok(mut log_handle) = OpenOptions::new()
                        .create(true)
                        .write(true)
                        .append(true)
                        .open(&log_file)
                    {
                        let _ = writeln!(log_handle, "[NexusForge Desktop] 后端启动失败: {}", e);
                    }
                    return Err(Box::new(e));
                }
            };

            // 存到 state 以便退出时 kill
            let state = app.state::<BackendState>();
            *state.0.lock().unwrap() = Some(child);

            // 健康检查放到后台线程，不阻塞窗口显示
            let log_file_clone = log_file.clone();
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                let start = Instant::now();
                let mut connected = false;
                loop {
                    if start.elapsed() > Duration::from_secs(60) {
                        if let Ok(mut h) = OpenOptions::new()
                            .create(true)
                            .write(true)
                            .append(true)
                            .open(&log_file_clone)
                        {
                            let _ = writeln!(
                                h,
                                "[NexusForge Desktop] 后端 60 秒内未通过健康检查"
                            );
                        }
                        break;
                    }
                    if std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok() {
                        std::thread::sleep(Duration::from_secs(1));
                        if let Ok(mut h) = OpenOptions::new()
                            .create(true)
                            .write(true)
                            .append(true)
                            .open(&log_file_clone)
                        {
                            let _ = writeln!(h, "[NexusForge Desktop] 后端健康检查通过");
                        }
                        connected = true;
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(500));
                }

                // 如果后端就绪，触发窗口重新加载（覆盖之前的错误页/白屏）
                if connected {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        let _ = window.eval("window.location.reload();");
                    }
                }
            });

            // setup 立即返回，窗口开始加载 URL（可能第一次失败，健康检查通过后会 reload）
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
