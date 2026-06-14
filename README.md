<div align="center">

# Nghia PC Toolkit

**Công cụ dòng lệnh tương tác trên Windows — kiểm tra hệ thống, dọn rác & chuẩn đoán nhanh chóng.**

![Version](https://img.shields.io/badge/version-v0.5.0-56d364?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-0078d4?style=flat-square&logo=windows)
![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

</div>

---

## ✨ Tính năng nổi bật

- 🖥️ **Menu mũi tên** — điều hướng dễ dàng bằng phím ↑/↓, không cần nhớ lệnh
- 📊 **Tổng quan (Dashboard)** — xem nhanh: RAM, ổ đĩa, mạng, tệp rác
- 🌐 **Kiểm tra Mạng** — ping, phân giải DNS, thử kết nối cổng TCP
- 📡 **Wi-Fi** — xem thông tin mạng và các cấu hình đã lưu
- 🧹 **Dọn rác an toàn** — quét thư mục Temp & Cache trình duyệt (có chế độ xem trước)
- 🎨 **3 Giao diện** — Carbon, Graphite, Matrix
- 📦 **Không cần cài Python** — đóng gói gọn nhẹ thành 1 file `.exe` duy nhất
- 🇻🇳 **Hỗ trợ Tiếng Việt** — giao diện và các lệnh đều có thể dùng bằng Tiếng Việt

---

## ⚡ Cài đặt nhanh

**Lệnh cài đặt tự động** (khuyên dùng):

```powershell
powershell -c "irm https://github.com/nghianghichcode/command-lab/raw/main/i.ps1|iex"
```

> Lệnh này sẽ tải bản release mới nhất, cài vào `%LOCALAPPDATA%\NghiaPCToolkit`,  
> tự động thêm vào biến môi trường `PATH`, và mở ứng dụng lên ngay lập tức.

**Sau khi cài xong**, bạn chỉ cần mở một terminal mới và gõ:

```
pctool
```

Hoặc mở trong một cửa sổ terminal riêng biệt:

```
pctool-window
```

---

## 🧰 Các lệnh hỗ trợ

> Công cụ sẽ hiện một **Menu tương tác** ngay khi khởi động — dùng phím mũi tên để di chuyển và nhấn Enter để chọn.  
> Bạn cũng có thể gõ trực tiếp bất kỳ lệnh nào.

| Lệnh / Bí danh | Chức năng |
|---|---|
| `dashboard` / `tongquan` | Xem tổng quan sức khỏe PC — RAM, ổ đĩa, mạng, rác |
| `system` / `hethong` | OS, CPU, RAM, người dùng, quyền admin |
| `disk` / `odia` | Dung lượng các ổ đĩa và cảnh báo nếu đầy |
| `network` / `mang` | IP nội bộ, kiểm tra DNS, Ping & kết nối TCP |
| `wifi` | Trạng thái Wi-Fi và tên các mạng đã lưu |
| `wifi settings` | Mở cài đặt Wi-Fi của Windows |
| `ports <host> <port>` | Kiểm tra kết nối TCP — VD: `ports github.com 443` |
| `apps [tên]` / `ungdung` | Tìm kiếm các ứng dụng trong Start Menu |
| `open <tên>` / `mo` | Mở thư mục / ứng dụng / cài đặt — VD: `open chrome` |
| `processes [n]` / `tientrinh` | Xem top các tiến trình đang ngốn nhiều RAM nhất |
| `temp` / `quetrac` | Quét thư mục temp và cache trình duyệt |
| `cleanup` / `donrac` | Xem trước các tệp rác sẽ bị xóa (chưa xóa thật) |
| `cleanup --apply` | Xóa các tệp rác sau khi xác nhận bằng cách gõ `XOA` |
| `recycle --empty` | Dọn sạch Thùng rác sau khi xác nhận bằng cách gõ `TRONG` |
| `startup` / `khoidong` | Liệt kê các tệp khởi động cùng Windows |
| `path` | Xem các đường dẫn trong biến môi trường PATH |
| `report` / `baocao` | Xuất báo cáo chẩn đoán đầy đủ ra màn hình Desktop |
| `theme` / `giaodien` | Đổi màu giao diện: `carbon`, `graphite`, `matrix` |
| `history` / `lichsu` | Xem lại các lệnh đã gõ |
| `clear` / `xoa` | Xóa sạch màn hình và vẽ lại |
| `exit` / `thoat` | Đóng công cụ |

> 🔒 **Mặc định an toàn tuyệt đối.** Chức năng dọn rác sẽ không xóa bất kỳ file nào nếu không có cờ `--apply` và sự xác nhận của bạn.

---

## 🎨 Giao diện (Themes)

| Tên Giao diện | Mô tả |
|---|---|
| `carbon` | Xanh đậm — Mặc định |
| `graphite` | Hổ phách, vàng cam ấm áp |
| `matrix` | Xanh lá trên nền đen |

```
theme carbon
theme graphite
theme matrix
```

---

## 🛠️ Biên dịch & Phát hành

Biên dịch thành file `.exe` độc lập:

```powershell
powershell -ExecutionPolicy Bypass -File .\make-package.ps1
```

Cập nhật mã nguồn + tạo GitHub Release:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-github.ps1
```

Chạy trực tiếp từ mã nguồn Python (không cần biên dịch):

```powershell
python -B terminal_ui.py
```

---

## 📋 Yêu cầu hệ thống

- Windows 10 / 11
- Không yêu cầu cài đặt Python nếu dùng bản `.exe`
- Python 3.9+ nếu bạn muốn chạy từ mã nguồn

---

<div align="center">

Made with ❤️ by [nghianghichcode](https://github.com/nghianghichcode)

</div>
