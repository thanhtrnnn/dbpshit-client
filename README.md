# DB PTIT Client

Một client Python để giải và nộp bài tập cơ sở dữ liệu trên `db.ptit.edu.vn`. Công cụ này tự động hóa quá trình đăng nhập, cho phép tìm kiếm và xem bài tập cục bộ, đồng thời cung cấp quy trình liền mạch để chạy và nộp các câu lệnh SQL.

## Tính năng

-   **Tự động đăng nhập**: Sử dụng Selenium để đăng nhập và trích xuất JWT token tự động.
-   **Tìm kiếm & Duyệt bài tập**: Tìm kiếm theo từ khóa hoặc duyệt theo chủ đề (Section). Hỗ trợ lọc bài tập theo trạng thái (AC, Chưa làm, ...).
-   **Hiển thị trên trình duyệt**: Xem mô tả bài tập trực tiếp trên trình duyệt web mặc định của bạn.
-   **Thực thi SQL**: Chạy thử các câu lệnh SQL với API để kiểm tra giải pháp của bạn (Dry Run).
-   **Nộp bài & Lịch sử**: Nộp giải pháp, nhận phản hồi ngay lập tức và xem lại lịch sử các lần nộp trước đó.
-   **Định dạng kết quả**: Kết quả truy vấn được hiển thị dưới dạng bảng sạch sẽ, dễ đọc.
-   **Xử lý lỗi**: Thông báo lỗi rõ ràng cho các vấn đề phổ biến như "Access Denied" hoặc lỗi cú pháp SQL.
-   **Làm sạch Payload**: Tự động xóa các comment khỏi SQL của bạn trước khi nộp để tránh lỗi API.
-   **Tự động chọn loại DB**: Tự động lấy ID loại cơ sở dữ liệu từ API cho từng bài tập.

## Yêu cầu

-   Python 3.x

## Cài đặt

1.  **Clone repository**.
Với Windows có giới hạn đường dẫn 260 ký tự, bạn nên làm theo các bước sau để tránh lỗi khi clone repo:
    > Tránh lỗi hiển thị tiếng Việt bị méo trong các file HTML: Đầu tiên chạy `chcp 65001` để chuyển sang UTF-8.
-   Mở PowerShell với quyền Administrator và bật hỗ trợ đường dẫn dài của Git:

    ```powershell
    git config --system core.longpaths true
    ```

-   Clone repo về một đường dẫn ngắn để tránh tràn 260 ký tự (ví dụ `C:\src` hoặc `D:\code`):

    ```powershell
    cd C:\src
    git clone https://github.com/thanhtrnnn/dbpshit-client.git
    ```

-   Nếu đã clone và gặp lỗi với các file dài, hãy xóa thư mục cũ, chạy lệnh `core.longpaths` ở trên rồi clone lại vào đường dẫn ngắn.



2.  **Thiết lập môi trường ảo và cài đặt thư viện**:
    Khuyến nghị sử dụng môi trường ảo để tránh xung đột thư viện.

    ```bash
    # Tạo môi trường ảo
    python -m venv .venv

    # Kích hoạt môi trường ảo
    # Trên Windows:
    .venv\Scripts\activate

    # Cài đặt các thư viện phụ thuộc
    pip install -r requirements.txt
    ```

3.  **Cấu hình môi trường**:
    **Copy file `.env.example` và đổi tên** thành `.env` trong **thư mục gốc** với các biến sau:
    ```env
    QLDT_USERNAME=tên_đăng_nhập_của_bạn
    QLDT_PASSWORD=mật_khẩu_của_bạn
    LOGIN_URL=https://dbapi.ptit.edu.vn/api/auth/auth/ptit-login
    BASE_API_URL=https://dbapi.ptit.edu.vn/api/app
    AUTH_API_URL=https://dbapi.ptit.edu.vn/api/auth
    DEFAULT_DB_TYPE=11111111-1111-1111-1111-111111111111
    USER_ID=
    ```
    > *Lưu ý*: 
    > - `USER_ID` được script tự điền nếu thiếu, hãy để trống giá trị này.
    > - `DEFAULT_DB_TYPE` là loại cơ sở dữ liệu mặc định (thường là MySQL với mã toàn số 1) nếu không lấy được từ API.

## Hướng dẫn sử dụng

1.  **Chạy client**:
    ```bash
    python client.py
    ```
    > Hướng dẫn cho gà mờ:
    > - Mày sẽ thấy menu tương tác trong terminal. 
    > - Chọn 1 để tìm kiếm bài tập hoặc 2 để duyệt theo dạng bài. 
    > - Nhập số thứ tự hiển thị trước tên bài tập để chọn. Trình duyệt sẽ mở đề bài.
    > - Làm bài trong `solution.sql`, sau đó quay lại menu để chạy thử (3) hoặc nộp bài (4).

2.  **Các tùy chọn Menu**:
    - Giao diện ban đầu:
        -   **1. Tìm kiếm bài tập (Local)**: Nhập từ khóa để tìm kiếm bài tập trong thư mục `problems/`. Hỗ trợ lọc theo trạng thái (Đã làm, Chưa làm, Đang làm).
        -   **2. Duyệt bài tập theo Section**: Duyệt bài tập theo cấu trúc thư mục/chương. Hỗ trợ lọc theo trạng thái.
    - Giao diện sau khi chọn bài:
        -   **3. Chạy thử code**: (Chỉ hiện khi đã chọn bài) Thực thi mã SQL hiện có trong `solution.sql` với bài tập đã chọn.
        -   **4. Nộp bài**: (Chỉ hiện khi đã chọn bài) Nộp mã SQL trong `solution.sql` để chấm điểm.
        -   **5. Xem lịch sử nộp bài**: (Chỉ hiện khi đã chọn bài) Xem lại lịch sử các lần nộp trước đó của bài tập hiện tại.
    -   **0. Thoát**: Thoát ứng dụng.

3.  **Quy trình làm việc**:
    -   Chọn tùy chọn **1** hoặc **2** để tìm/chọn bài tập.
    -   Trong danh sách bài tập, bạn có thể lọc theo trạng thái: `[A]ll`, `[C]ompleted` (AC), `[T]ried`, `[U]nsubmitted`.
    -   Sau khi chọn, bài tập sẽ mở trong trình duyệt và file `solution.sql` sẽ được tạo/cập nhật.
    -   Mở `solution.sql` trong trình soạn thảo của bạn (VS Code, Notepad, ...).
    -   Viết câu lệnh SQL của bạn vào `solution.sql` (bên dưới phần header).
    -   Quay lại menu chính, chọn tùy chọn **3** để kiểm tra thử (Dry Run).
    -   Chọn tùy chọn **4** để nộp bài và nhận kết quả chấm.
    -   Chọn tùy chọn **5** nếu muốn xem lại lịch sử nộp bài.

## Khắc phục sự cố

-   **Đăng nhập thất bại**: Kiểm tra `QLDT_USERNAME` và `QLDT_PASSWORD` trong `.env`. Đảm bảo Chrome đã được cài đặt.
-   **Access Denied (401)**: Token có thể đã hết hạn. Khởi động lại script để đăng nhập lại.
-   **Trình duyệt không mở**: Đảm bảo hệ thống của bạn đã cấu hình trình duyệt mặc định.
-   **FileNotFoundError**: Đảm bảo thư mục `problems/` tồn tại và chứa các file `.html`.

## Cấu trúc thư mục

-   `client.py`: Script ứng dụng chính.
-   `problems/`: Thư mục chứa các file HTML bài tập.
-   `solution.sql`: File tạm thời để viết code SQL của bạn.
-   `.env`: File cấu hình (chứa thông tin nhạy cảm).
-   `requirements.txt`: Các thư viện Python phụ thuộc.
