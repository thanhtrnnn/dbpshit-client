# DB PTIT Client

Một client Python để giải và nộp bài tập cơ sở dữ liệu trên `db.ptit.edu.vn`. Công cụ này tự động hóa quá trình đăng nhập, cho phép tìm kiếm và xem bài tập cục bộ, đồng thời cung cấp quy trình liền mạch để chạy và nộp các câu lệnh SQL.

## Tính năng

-   **Tự động đăng nhập**: Sử dụng Selenium để đăng nhập và trích xuất JWT token tự động.
-   **Tìm kiếm bài tập cục bộ**: Tìm kiếm các bài tập được lưu trữ cục bộ trong thư mục `problems/`.
-   **Hiển thị trên trình duyệt**: Xem mô tả bài tập trực tiếp trên trình duyệt web mặc định của bạn.
-   **Thực thi SQL**: Chạy thử các câu lệnh SQL với API để kiểm tra giải pháp của bạn (Dry Run).
-   **Nộp bài**: Nộp giải pháp SQL của bạn và nhận phản hồi ngay lập tức (AC, WA, v.v.).
-   **Định dạng kết quả**: Kết quả truy vấn được hiển thị dưới dạng bảng sạch sẽ, dễ đọc.
-   **Xử lý lỗi**: Thông báo lỗi rõ ràng cho các vấn đề phổ biến như "Access Denied" hoặc lỗi cú pháp SQL.
-   **Làm sạch Payload**: Tự động xóa các comment khỏi SQL của bạn trước khi nộp để tránh lỗi API.
-   **Tự động chọn loại DB**: Tự động lấy ID loại cơ sở dữ liệu từ API cho từng bài tập.

## Yêu cầu

-   Python 3.x
-   Google Chrome (cho Selenium)
-   Chromedriver (tương thích với phiên bản Chrome của bạn)

## Cài đặt

1.  **Clone repository** (nếu có) hoặc tải mã nguồn.

2.  **Cài đặt các thư viện phụ thuộc**:
    ```bash
    pip install -r requirements.txt
    ```
    *Các thư viện bao gồm: `requests`, `beautifulsoup4`, `selenium`, `python-dotenv`.*

3.  **Cấu hình môi trường**:
    Tạo một file `.env` trong thư mục gốc với các biến sau:
    ```env
    QLDT_USERNAME=tên_đăng_nhập_của_bạn
    QLDT_PASSWORD=mật_khẩu_của_bạn
    LOGIN_URL=https://qldt.ptit.edu.vn
    BASE_API_URL=https://dbapi.ptit.edu.vn/api
    DEFAULT_DB_TYPE=11111111-1111-1111-1111-111111111111
    USER_ID=uuid_người_dùng_của_bạn
    ```
    > *Lưu ý*: 
    > - `USER_ID` có thể được lấy tự động hoặc nhập thủ công nếu thiếu.
    > - `DEFAULT_DB_TYPE` là loại cơ sở dữ liệu mặc định (thường là MySQL) nếu không lấy được từ API.

## Hướng dẫn sử dụng

1.  **Chạy client**:
    ```bash
    python client.py
    ```

2.  **Các tùy chọn Menu**:
    -   **1. Tìm kiếm bài tập (Local)**: Nhập từ khóa để tìm kiếm bài tập trong thư mục `problems/`. Chọn một bài tập để xem trên trình duyệt và tạo file `solution.sql`.
    -   **2. Nhập ID bài tập trực tiếp**: (Hiện đang bị vô hiệu hóa trong chế độ local).
    -   **3. Chạy thử code**: Thực thi mã SQL hiện có trong `solution.sql` với bài tập đã chọn. Hiển thị bảng kết quả hoặc thông báo lỗi.
    -   **4. Nộp bài**: Nộp mã SQL trong `solution.sql` để chấm điểm. Hiển thị trạng thái (Chấp nhận, Sai kết quả, v.v.) và kết quả test case.
    -   **0. Thoát**: Thoát ứng dụng.

3.  **Quy trình làm việc**:
    -   Chọn tùy chọn **1** để tìm bài tập.
    -   Bài tập sẽ mở trong trình duyệt của bạn.
    -   Mở `solution.sql` trong trình soạn thảo của bạn.
    -   Viết câu lệnh SQL của bạn vào `solution.sql` (bên dưới phần header).
    -   Chọn tùy chọn **3** để kiểm tra câu lệnh của bạn.
    -   Chọn tùy chọn **4** để nộp bài khi đã sẵn sàng.

## Khắc phục sự cố

-   **Đăng nhập thất bại**: Kiểm tra `QLDT_USERNAME` và `QLDT_PASSWORD` trong `.env`. Đảm bảo Chrome đã được cài đặt.
-   **Access Denied (401)**: Token có thể đã hết hạn. Khởi động lại script để đăng nhập lại. Ngoài ra, đảm bảo SQL của bạn không chứa từ khóa bị cấm (mặc dù comment đã được tự động xóa).
-   **Trình duyệt không mở**: Đảm bảo hệ thống của bạn đã cấu hình trình duyệt mặc định.
-   **FileNotFoundError**: Đảm bảo thư mục `problems/` tồn tại và chứa các file `.html`.

## Cấu trúc thư mục

-   `client.py`: Script ứng dụng chính.
-   `problems/`: Thư mục chứa các file HTML bài tập.
-   `solution.sql`: File tạm thời để viết giải pháp SQL của bạn.
-   `.env`: File cấu hình (chứa thông tin nhạy cảm).
-   `requirements.txt`: Các thư viện Python phụ thuộc.
