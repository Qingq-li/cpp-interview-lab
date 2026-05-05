#include <iostream>
#include <fstream>
#include <stdexcept>
#include <string>

// ---------- 模块 1：配置加载（适合用 exception） ----------
std::string load_config(const std::string& path) {
    std::ifstream file(path);
    if (!file) {
        throw std::runtime_error("Failed to open config file: " + path);
    }

    std::string content;
    file >> content;

    if (content.empty()) {
        throw std::runtime_error("Config is empty");
    }

    return content;
}

// ---------- 模块 2：初始化 ----------
void init_system() {
    std::string config = load_config("config.txt");
    std::cout << "Config loaded: " << config << std::endl;
}

// ---------- 模块 3：运行循环（不用 exception） ----------
bool process_step(int step) {
    if (step == 3) {
        // 模拟错误（比如传感器异常）
        return false;
    }

    std::cout << "Processing step " << step << std::endl;
    return true;
}

// ---------- 主程序 ----------
int main() {
    try {
        // 🔹 初始化阶段（可能 throw）
        init_system();

        // 🔹 实时循环（不要 throw）
        for (int i = 0; i < 5; ++i) {
            if (!process_step(i)) {
                std::cerr << "Warning: step failed, continue...\n";
                continue;
            }
        }

        std::cout << "System finished normally\n";
    }
    catch (const std::exception& e) {
        // 🔥 统一错误处理
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return -1;
    }

    return 0;
}