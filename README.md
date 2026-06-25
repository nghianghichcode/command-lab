<div align="center">

<pre>
 _   _  ____ _   _ ___    _       ____   ____
| \ | |/ ___| | | |_ _|  / \     |  _ \ / ___|
|  \| | |  _| |_| || |  / _ \    | |_) | |
| |\  | |_| |  _  || | / ___ \   |  __/| |___
|_| \_|\____|_| |_|___/_/   \_\  |_|    \____|
                 T O O L K I T
</pre>

**🚀 Đưa trải nghiệm quản lý hệ thống Windows của bạn lên một tầm cao mới.**

[![Version](https://img.shields.io/badge/version-v0.6.0-00E676?style=for-the-badge&logo=appveyor)](https://github.com/nghianghichcode/command-lab/releases)
[![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=for-the-badge&logo=windows)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-FF6D00?style=for-the-badge)](LICENSE)

</div>

---

## ⚡ TỐI THƯỢNG & MẠNH MẼ

Nghia PC Toolkit không chỉ là một công cụ dòng lệnh (CLI). Đây là một hệ thống **Dashboard tương tác** siêu mượt mà, biến Terminal nhàm chán của Windows thành một buồng lái chuyên nghiệp. Tích hợp các thuật toán chẩn đoán mạng, quản lý ứng dụng, giải phóng bộ nhớ và giám sát tiến trình - tất cả gói gọn trong một file `pctool.exe` duy nhất.

### 🌟 Tính Năng Đột Phá
- ❤️ **Chấm Điểm Sức Khỏe Máy:** Điểm 0-100 kèm khuyến nghị tối ưu.
- 🔋 **Trợ Lý Pin Laptop:** Xem mức pin, trạng thái sạc và thời gian còn lại.
- 🎯 **Điều hướng bằng mũi tên (Arrow-key Navigation):** Tạm biệt việc phải gõ lệnh thủ công. Cuộn và chọn ứng dụng mượt mà không độ trễ.
- 🧹 **Dọn Rác Chuẩn Xác (Smart Cleanup):** Quét sâu vào Cache trình duyệt và thư mục Temp mà không ảnh hưởng đến hệ thống.
- 📡 **Chẩn Đoán Mạng Chuyên Sâu:** Ping, kiểm tra cổng TCP, soi trạng thái DNS và Wi-Fi chỉ trong 1 giây.
- 🔍 **Tìm & Mở Nhanh Ứng Dụng:** Bộ lọc ứng dụng thông minh, gạt bỏ mọi shortcut rác, tìm đúng app bạn cần.
- 🎨 **Cá Nhân Hóa Đỉnh Cao:** Các chủ đề `carbon`, `graphite`, `matrix` siêu ngầu, tối ưu cho màn hình OLED.

---

## 🚀 CÀI ĐẶT THẦN TỐC (1 Click)

Mở **PowerShell** (hoặc Windows Terminal) với quyền Admin và dán dòng mã quyền năng này:

```powershell
powershell -c "irm https://github.com/nghianghichcode/command-lab/raw/main/i.ps1|iex"
```

> **🔥 Kết quả:** Tool sẽ tự động tải lõi `pctool.exe` mới nhất, âm thầm thiết lập biến môi trường và khởi động ngay lập tức. Bạn không cần cài đặt Python hay bất kỳ thư viện nào!

Lần sau muốn gọi, chỉ cần gõ:
```bash
pctool
```
Hoặc mở cửa sổ riêng cực ngầu: `pctool-window`

---

## 💻 KHO VŨ KHÍ (COMMANDS)

Bạn có thể dùng mũi tên để chọn trực tiếp trên menu, hoặc gõ nhanh các lệnh sau (hỗ trợ Tiếng Việt 100%):

### 🛡️ Hệ Thống & Quản Lý
| Lệnh / Bí danh | Chức năng |
|:---|:---|
| 📊 `dashboard` / `tongquan` | Mở bảng điều khiển tổng hợp: CPU, RAM, Ổ đĩa, Mạng, Rác |
| ❤️ `health` / `suckhoe` | Chấm điểm sức khỏe máy và khuyến nghị tối ưu |
| 🔋 `battery` / `pin` | Xem pin laptop, nguồn sạc và thời gian còn lại |
| 🖥️ `system` / `hethong` | Quét cấu hình máy, kiến trúc CPU, quyền User/Admin |
| 💾 `disk` / `odia` | Phân tích không gian ổ cứng, cảnh báo dung lượng đỏ |
| 🚀 `startup` / `khoidong` | Soi các ứng dụng chạy ngầm khởi động cùng Windows |
| ⚙️ `processes` / `tientrinh` | Triệu hồi danh sách tiến trình "ngốn" RAM nhất |

### 🌐 Mạng & Kết Nối
| Lệnh / Bí danh | Chức năng |
|:---|:---|
| 📡 `network` / `mang` | Thông tin IP nội bộ/Public, DNS, Ping |
| 📶 `wifi` | Truy xuất cấu hình Wi-Fi và mật khẩu đã lưu |
| 🔌 `ports <host> <port>` | Ping cổng TCP (VD: `ports google.com 443`) |

### 🔍 Công Cụ Hỗ Trợ
| Lệnh / Bí danh | Chức năng |
|:---|:---|
| 🎯 `apps [tên]` / `ungdung` | Tìm và mở nhanh phần mềm (tự động lọc rác) |
| 📂 `open <tên>` / `mo` | Mở ứng dụng, web, thư mục siêu tốc |
| 🧹 `temp` / `quetrac` | Quét phân tích các file rác, bộ nhớ đệm ẩn |
| 💥 `cleanup --apply` | Phá hủy rác hệ thống (yêu cầu xác nhận an toàn) |
| 🗑️ `recycle --empty` | Xóa sổ Thùng Rác (không thể phục hồi) |
| 🎨 `theme` / `giaodien` | Chuyển đổi giao diện `carbon`, `graphite`, `matrix` |
| 📜 `report` / `baocao` | Xuất file log chẩn đoán chuyên sâu ra Desktop |

> 🔒 **Cơ Chế An Toàn Kép:** Mọi hành động phá hủy (`cleanup`, `recycle`) đều bị chặn tự động trừ khi bạn cố tình thêm cờ `--apply` hoặc `--empty` và nhập mã xác nhận.

---

## 🛠️ DÀNH CHO DEVELOPER (Build & Deploy)

Nếu bạn muốn tùy biến mã nguồn và tự build cho riêng mình:

**1. Biên dịch siêu tốc (`.exe`):**
```powershell
powershell -ExecutionPolicy Bypass -File .\make-package.ps1
```

**2. Đẩy lên GitHub Release:**
```powershell
powershell -ExecutionPolicy Bypass -File .\publish-github.ps1
```

**3. Chạy Live (Dành cho Dev):**
```bash
python -B terminal_ui.py
```

---

<div align="center">

Được rèn đúc từ những dòng lệnh tinh túy nhất bởi [**nghianghichcode**](https://github.com/nghianghichcode).  
Bản quyền 2026. Keep hacking! 💻🔥

</div>
