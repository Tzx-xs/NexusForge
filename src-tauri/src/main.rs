#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::Manager;

struct AppState {
    project_dir: Mutex<Option<String>>,
}

#[tauri::command]
fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn set_project_dir(path: String, state: tauri::State<AppState>) -> Result<(), String> {
    let mut dir = state.project_dir.lock().map_err(|e| e.to_string())?;
    *dir = Some(path);
    Ok(())
}

#[tauri::command]
fn get_project_dir(state: tauri::State<AppState>) -> Option<String> {
    state.project_dir.lock().ok().and_then(|d| d.clone())
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            project_dir: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            get_app_version,
            set_project_dir,
            get_project_dir,
        ])
        .run(tauri::generate_context!())
        .expect("error while running xingyuanbi application");
}
