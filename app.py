from datetime import date
import uuid
import re
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = "CSDL"


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def required(form, key, label):
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"Vui lòng nhập {label}.")
    return value


def friendly_error(exc, action="thực hiện yêu cầu"):
    """Không để lộ thông tin SQL/kết nối nội bộ ra giao diện."""
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, Error):
        code = getattr(exc, "errno", None)
        messages = {
            1062: "Thông tin vừa nhập đã tồn tại trong hệ thống (ví dụ: CCCD, số điện thoại hoặc email). Vui lòng kiểm tra và sử dụng thông tin khác.",
            1452: "Dữ liệu liên quan không tồn tại hoặc chưa được đăng ký. Vui lòng kiểm tra lại khách hàng, sản phẩm, nhân viên hoặc shipper.",
            1451: "Không thể thực hiện vì dữ liệu này đang được sử dụng bởi đơn hàng hoặc dữ liệu liên quan.",
            1048: "Có trường thông tin bắt buộc đang bị bỏ trống. Vui lòng kiểm tra lại biểu mẫu.",
            1406: "Một trong các thông tin nhập vào quá dài so với giới hạn cho phép.",
            3819: "Dữ liệu không đáp ứng quy tắc nghiệp vụ. Vui lòng kiểm tra giá trị đã nhập.",
            1264: "Giá trị số vượt quá giới hạn cho phép.",
            1146: "Một bảng dữ liệu cần thiết chưa tồn tại. Vui lòng liên hệ quản trị viên để kiểm tra cấu trúc cơ sở dữ liệu.",
            1054: "Cấu trúc cơ sở dữ liệu chưa đồng bộ với ứng dụng. Vui lòng liên hệ quản trị viên.",
        }
        if code in messages:
            return messages[code]
        if code in (2002, 2003, 2005, 1045):
            return "Không thể kết nối cơ sở dữ liệu. Vui lòng thử lại sau hoặc liên hệ quản trị viên."
        return f"Hệ thống chưa thể {action} do lỗi dữ liệu hoặc máy chủ. Vui lòng thử lại; nếu lỗi tiếp tục, hãy liên hệ quản trị viên."
    if isinstance(exc, (ValueError, TypeError)):
        return "Thông tin nhập vào không đúng định dạng. Vui lòng kiểm tra lại."
    return f"Không thể {action}. Vui lòng kiểm tra thông tin và thử lại."


def fetch_all(sql, params=()):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def load_invoice(order_id, customer_cccd=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """SELECT d.MaDH AS order_id, d.NgayDat AS order_date,
            d.NgayTT AS payment_date, d.TrangThai AS order_status, d.PhuongThucTT AS payment_method,
            d.GhiChu AS note, d.TenNguoiNhan AS recipient, d.SDTNguoiNhan AS recipient_phone,
            d.DiaChiNhanHang AS recipient_address, nd.CCCD AS customer_cccd, nd.HoTen AS customer_name
            FROM DON_HANG d JOIN NGUOI_DUNG nd ON nd.CCCD=d.CCCD_KH WHERE d.MaDH=%s"""
        params = [order_id]
        if customer_cccd is not None:
            sql += " AND d.CCCD_KH=%s"
            params.append(customer_cccd)
        cursor.execute(sql, tuple(params))
        header = cursor.fetchone()
        if not header:
            return None
        cursor.execute("""SELECT sp.MaSP AS product_id, sp.TenSP AS product_name,
            ct.SoLuong AS quantity, sp.DonGia AS unit_price, ct.SoLuong*sp.DonGia AS line_total
            FROM CT_DON_HANG ct JOIN SAN_PHAM sp ON sp.MaSP=ct.MaSP
            WHERE ct.MaDH=%s ORDER BY sp.TenSP""", (order_id,))
        items = cursor.fetchall()
        total = sum((item["line_total"] for item in items), start=0)
        return {"header": header, "items": items, "total": total}
    finally:
        cursor.close()
        conn.close()


@app.route("/")
def home():
    return render_template("home.html")


# -------------------- CUSTOMER ENDPOINT --------------------
@app.route("/user")
def user_portal():
  products, customer_orders = [], []
  lookup_cccd = request.args.get("customer_cccd", "").strip()
  try:
    # Lấy thêm tổng tồn kho từ bảng LUU_TRU
    products = fetch_all("""
            SELECT sp.MaSP, sp.TenSP, sp.DonGia,
                   COALESCE(SUM(lt.SoLuongTon), 0) AS TongTonKho
            FROM SAN_PHAM sp
            LEFT JOIN LUU_TRU lt ON lt.MaSP = sp.MaSP
            GROUP BY sp.MaSP, sp.TenSP, sp.DonGia
            ORDER BY sp.TenSP
        """)
    if lookup_cccd:
      if not re.fullmatch(r"\d{12}", lookup_cccd):
        flash("CCCD tra cứu phải gồm đúng 12 chữ số.", "error")
      else:
        customer_orders = fetch_all(
            """SELECT MaDH, NgayDat, TrangThai, TenNguoiNhan,
                    DiaChiNhanHang FROM DON_HANG WHERE CCCD_KH=%s ORDER BY NgayDat DESC""",
            (lookup_cccd,),
        )
        if not customer_orders:
          flash("Không tìm thấy đơn hàng nào thuộc CCCD này.", "error")
  except Error as exc:
    flash(f"Không thể tải dữ liệu: {friendly_error(exc, 'tải dữ liệu')}", "error")
  return render_template(
      "user.html",
      products=products,
      customer_orders=customer_orders,
      lookup_cccd=lookup_cccd,
  )


@app.post("/user/register")
def create_customer():
    conn = cursor = None
    try:
        cccd = required(request.form, "cccd", "CCCD")
        if not re.fullmatch(r"\d{12}", cccd):
            raise ValueError("CCCD phải gồm đúng 12 chữ số.")
        name = required(request.form, "name", "họ tên")
        if len(name) < 2 or not re.fullmatch(r"[\wÀ-ỹ\s.'-]+", name, re.UNICODE):
            raise ValueError("Họ tên phải có ít nhất 2 ký tự và không chứa ký tự đặc biệt không hợp lệ.")
        phone = required(request.form, "phone", "số điện thoại")
        if not re.fullmatch(r"0\d{9,10}", phone):
            raise ValueError("Số điện thoại phải bắt đầu bằng 0 và gồm 10 hoặc 11 chữ số.")
        email = request.form.get("email", "").strip()
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Email không đúng định dạng, ví dụ ten@email.com.")
        birth_date = request.form.get("birth_date") or None
        if birth_date:
            try:
                parsed = date.fromisoformat(birth_date)
                if parsed >= date.today():
                    raise ValueError("Ngày sinh phải nhỏ hơn ngày hiện tại.")
            except ValueError:
                raise ValueError("Ngày sinh không hợp lệ. Vui lòng chọn ngày có thật trong quá khứ.")
        gender = request.form.get("gender") or None
        address = request.form.get("address", "").strip() or None

        conn = get_connection()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # Bước 1: Kiểm tra CCCD trong bảng gốc NGUOI_DUNG
        cursor.execute(
            "SELECT HoTen FROM NGUOI_DUNG WHERE CCCD = %s FOR UPDATE", (cccd,)
        )
        existing_user = cursor.fetchone()

        if not existing_user:
          # Người dùng hoàn toàn mới -> Thêm vào NGUOI_DUNG
          cursor.execute(
              """INSERT INTO NGUOI_DUNG (CCCD, HoTen, NgaySinh, GioiTinh)
                   VALUES (%s, %s, %s, %s)""",
              (cccd, name, birth_date, gender),
          )
        else:
          # Đã có CCCD -> Kiểm tra tên có khớp không để tránh nhập nhầm CCCD người khác
          if existing_user["HoTen"].strip().lower() != name.strip().lower():
            raise ValueError(
                f"CCCD {cccd} đã được đăng ký với họ tên khác.")
          # Cập nhật thêm ngày sinh / giới tính nếu người dùng có nhập bổ sung
          cursor.execute(
              """UPDATE NGUOI_DUNG
                   SET NgaySinh = COALESCE(%s, NgaySinh),
                       GioiTinh = COALESCE(%s, GioiTinh)
                   WHERE CCCD = %s""",
              (birth_date, gender, cccd),
          )

        # Bước 2: Đảm bảo có trong bảng KHACH_HANG và NGUOI_DUNG_VAITRO (không lỗi nếu đã tồn tại)
        cursor.execute(
            """INSERT INTO KHACH_HANG (CCCD, DiaChi) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE DiaChi = COALESCE(VALUES(DiaChi), DiaChi)""",
            (cccd, address),
        )
        cursor.execute(
            """INSERT IGNORE INTO NGUOI_DUNG_VAITRO (CCCD, VaiTro)
               VALUES (%s, 'Khách hàng')""",
            (cccd,),
        )

        # Bước 3: Xử lý thêm SĐT (Thuộc tính đa trị)
        cursor.execute(
            "SELECT CCCD FROM NGUOI_DUNG_SDT WHERE SDT = %s", (phone,)
        )
        phone_owner = cursor.fetchone()
        if phone_owner and phone_owner["CCCD"] != cccd:
          raise ValueError(
              "Số điện thoại này đã được sử dụng bởi một CCCD khác."
          )
        cursor.execute(
            "INSERT IGNORE INTO NGUOI_DUNG_SDT (CCCD, SDT) VALUES (%s, %s)",
            (cccd, phone),
        )

        # Bước 4: Xử lý thêm Email (Thuộc tính đa trị - nếu có nhập)
        if email:
          cursor.execute(
              "SELECT CCCD FROM NGUOI_DUNG_EMAIL WHERE Email = %s", (email,)
          )
          email_owner = cursor.fetchone()
          if email_owner and email_owner["CCCD"] != cccd:
            raise ValueError("Email này đã được sử dụng bởi một CCCD khác.")
          cursor.execute(
              """INSERT IGNORE INTO NGUOI_DUNG_EMAIL (CCCD, Email)
                   VALUES (%s, %s)""",
              (cccd, email),
          )

        conn.commit()
        flash(
            f"Cập nhật / Đăng ký thành công thông tin khách hàng {name}.",
            "success",
        )
    except (Error, ValueError, TypeError) as exc:
        if conn: conn.rollback()
        flash(f"Không thể đăng ký: {friendly_error(exc, 'đăng ký khách hàng')}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("user_portal") + "#register")


@app.post("/user/orders")
def create_order():
  conn = cursor = None
  try:
    cccd = required(request.form, "customer_cccd", "CCCD khách hàng")
    if not re.fullmatch(r"\d{12}", cccd):
      raise ValueError("CCCD khách hàng phải gồm đúng 12 chữ số.")
    selected = request.form.getlist("product_ids")
    if not selected:
      raise ValueError(
          "Bạn chưa chọn sản phẩm nào. Hãy chọn ít nhất một sản phẩm."
      )
    items = []
    for product_id in selected:
      try:
        qty = int(required(request.form, f"quantity_{product_id}", "số lượng"))
      except (TypeError, ValueError):
        raise ValueError("Số lượng sản phẩm phải là số nguyên dương.")
      if qty < 1:
        raise ValueError("Số lượng sản phẩm phải lớn hơn 0.")
      items.append((product_id, qty))

    recipient = required(request.form, "recipient", "tên người nhận")
    phone = required(request.form, "recipient_phone", "SĐT người nhận")
    if not re.fullmatch(r"0\d{9,10}", phone):
      raise ValueError(
          "SĐT người nhận phải bắt đầu bằng 0 và gồm 10 hoặc 11 chữ số."
      )
    address = required(request.form, "recipient_address", "địa chỉ nhận hàng")
    payment = request.form.get("payment_method", "").strip() or None
    note = request.form.get("note", "").strip() or None

    conn = get_connection()
    conn.start_transaction()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT CCCD FROM KHACH_HANG WHERE CCCD=%s", (cccd,))
    if not cursor.fetchone():
      raise ValueError(
          "Không tìm thấy khách hàng với CCCD này. Vui lòng đăng ký trước khi"
          " đặt hàng."
      )

    # KIỂM TRA TỒN KHO CHO TỪNG SẢN PHẨM
    for product_id, qty in items:
      cursor.execute(
          """
                SELECT sp.MaSP, sp.TenSP, COALESCE(SUM(lt.SoLuongTon), 0) AS TongTonKho
                FROM SAN_PHAM sp
                LEFT JOIN LUU_TRU lt ON lt.MaSP = sp.MaSP
                WHERE sp.MaSP = %s
                GROUP BY sp.MaSP, sp.TenSP
            """,
          (product_id,),
      )
      prod = cursor.fetchone()
      if not prod:
        raise ValueError(
            f"Sản phẩm có mã {product_id} không còn tồn tại. Vui lòng tải lại"
            " danh sách sản phẩm."
        )
      if qty > prod["TongTonKho"]:
        raise ValueError(
            f"Sản phẩm '{prod['TenSP']}' (Mã: {product_id}) không đủ hàng trong"
            f" kho! Hiện chỉ còn {prod['TongTonKho']} sản phẩm, nhưng bạn đang"
            f" đặt {qty}."
        )

    order_id = "DH" + uuid.uuid4().hex[:8].upper()
    cursor.execute(
        """INSERT INTO DON_HANG
            (MaDH, TrangThai, GhiChu, PhuongThucTT, TenNguoiNhan, SDTNguoiNhan, DiaChiNhanHang, CCCD_KH)
            VALUES (%s,'Chờ xác nhận',%s,%s,%s,%s,%s,%s)""",
        (order_id, note, payment, recipient, phone, address, cccd),
    )
    cursor.executemany(
        "INSERT INTO CT_DON_HANG (MaDH,MaSP,SoLuong) VALUES (%s,%s,%s)",
        [(order_id, pid, qty) for pid, qty in items],
    )
    conn.commit()
    flash(
        f"Đã tạo đơn {order_id}. Đơn đang chờ nhân viên xác nhận.", "success"
    )
  except (Error, ValueError, TypeError) as exc:
    if conn:
      conn.rollback()
    flash(
        f"Không thể đặt hàng: {friendly_error(exc, 'tạo đơn hàng')}", "error"
    )
  finally:
    if cursor:
      cursor.close()
    if conn:
      conn.close()
  return redirect(url_for("user_portal") + "#order")


@app.post("/user/orders/cancel")
def cancel_order():
    conn = cursor = None
    try:
        order_id = required(request.form, "order_id", "mã đơn hàng")
        cccd = required(request.form, "customer_cccd", "CCCD khách hàng")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""UPDATE DON_HANG SET TrangThai='Đã hủy'
                          WHERE MaDH=%s AND CCCD_KH=%s AND TrangThai='Chờ xác nhận'""", (order_id, cccd))
        if cursor.rowcount != 1:
            raise ValueError("Không thể hủy đơn. Có thể mã đơn không tồn tại, không thuộc CCCD này hoặc đơn đã được nhân viên xác nhận.")
        conn.commit()
        flash(f"Đã hủy đơn {order_id}.", "success")
    except (Error, ValueError) as exc:
        if conn: conn.rollback()
        flash(f"Không thể hủy đơn: {friendly_error(exc, 'hủy đơn hàng')}", "error")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return redirect(url_for("user_portal") + "#cancel")


@app.route("/user/invoice")
def customer_invoice():
    order_id = request.args.get("order_id", "").strip()
    cccd = request.args.get("customer_cccd", "").strip()
    invoice_data = None
    if not re.fullmatch(r"\d{12}", cccd):
        flash("CCCD không hợp lệ. Vui lòng tra cứu đơn hàng bằng đúng CCCD gồm 12 chữ số.", "error")
    elif not order_id:
        flash("Vui lòng cung cấp mã đơn hàng.", "error")
    else:
        try:
            invoice_data = load_invoice(order_id, cccd)
            if not invoice_data:
                flash("Không tìm thấy hóa đơn thuộc CCCD này. Hãy kiểm tra mã đơn và CCCD.", "error")
        except Error as exc:
            flash(f"Không thể xem hóa đơn: {friendly_error(exc, 'tải hóa đơn')}", "error")
    return render_template("invoice.html", invoice=invoice_data, staff_view=False,
                           customer_cccd=cccd)


# -------------------- STAFF ENDPOINT --------------------
@app.route("/staff")
def staff_portal():
  pending_orders, employees, orders, shippers, revenue_data = (
      [],
      [],
      [],
      [],
      {},
  )
  try:
    pending_orders = fetch_all(
        """SELECT d.MaDH, d.NgayDat, d.TenNguoiNhan, d.SDTNguoiNhan,
            d.DiaChiNhanHang, d.TrangThai, nd.HoTen AS customer_name, d.CCCD_KH
            FROM DON_HANG d JOIN NGUOI_DUNG nd ON nd.CCCD=d.CCCD_KH
            WHERE d.TrangThai='Chờ xác nhận' ORDER BY d.NgayDat"""
    )

    if pending_orders:
      order_items = fetch_all("""
                SELECT ct.MaDH, sp.TenSP, ct.SoLuong
                FROM CT_DON_HANG ct
                JOIN SAN_PHAM sp ON sp.MaSP = ct.MaSP
                JOIN DON_HANG d ON d.MaDH = ct.MaDH
                WHERE d.TrangThai = 'Chờ xác nhận'
                ORDER BY sp.TenSP
            """)
      summary_map = {}
      for item in order_items:
        summary_map.setdefault(item["MaDH"], []).append(
            f"{item['TenSP']} (SL: {item['SoLuong']})"
        )
      for o in pending_orders:
        o["items_summary"] = "<br>".join(summary_map.get(o["MaDH"], []))

    employees = fetch_all(
        """SELECT nv.CCCD, nd.HoTen FROM NV_BAN_HANG nv
            JOIN NGUOI_DUNG nd ON nd.CCCD=nv.CCCD ORDER BY nd.HoTen"""
    )
    shippers = fetch_all(
        """SELECT s.CCCD, nd.HoTen, s.KhuVuc, s.BienSo, s.LoaiXe
            FROM SHIPPER s JOIN NGUOI_DUNG nd ON nd.CCCD=s.CCCD ORDER BY nd.HoTen"""
    )
    
    # Lấy toàn bộ danh sách đơn hàng cho tab quản lý
    orders = fetch_all("""SELECT d.MaDH, d.NgayDat, d.TrangThai, d.TenNguoiNhan,
            d.SDTNguoiNhan, d.DiaChiNhanHang, nd.HoTen AS customer_name,
            vc.MaVC, vc.TrangThaiGiao, vc.NgayGiao, vc.TienCOD, vc.CCCD_Shipper,
            ns.HoTen AS shipper_name, s.KhuVuc, s.BienSo, s.LoaiXe
            FROM DON_HANG d JOIN NGUOI_DUNG nd ON nd.CCCD=d.CCCD_KH
            LEFT JOIN VAN_CHUYEN vc ON vc.MaDH=d.MaDH
            LEFT JOIN SHIPPER s ON s.CCCD=vc.CCCD_Shipper
            LEFT JOIN NGUOI_DUNG ns ON ns.CCCD=s.CCCD
            ORDER BY d.NgayDat DESC""")

    # --- TÍNH TOÁN BÁO CÁO DOANH THU (Chỉ tính các đơn 'Đã giao') ---
    revenue_rows = fetch_all("""
            SELECT 
                COALESCE(SUM(ct.SoLuong * sp.DonGia), 0) AS total_revenue,
                COUNT(DISTINCT d.MaDH) AS total_success_orders
            FROM DON_HANG d
            JOIN CT_DON_HANG ct ON ct.MaDH = d.MaDH
            JOIN SAN_PHAM sp ON sp.MaSP = ct.MaSP
            WHERE d.TrangThai = 'Đã giao'
        """)
    
    # Doanh thu chi tiết theo từng sản phẩm bán được
    product_sales = fetch_all("""
            SELECT sp.MaSP, sp.TenSP, 
                   SUM(ct.SoLuong) AS total_qty, 
                   SUM(ct.SoLuong * sp.DonGia) AS total_amount
            FROM DON_HANG d
            JOIN CT_DON_HANG ct ON ct.MaDH = d.MaDH
            JOIN SAN_PHAM sp ON sp.MaSP = ct.MaSP
            WHERE d.TrangThai = 'Đã giao'
            GROUP BY sp.MaSP, sp.TenSP
            ORDER BY total_amount DESC
        """)

    revenue_data = {
        "total_revenue": revenue_rows[0]["total_revenue"] if revenue_rows else 0,
        "total_success_orders": revenue_rows[0]["total_success_orders"] if revenue_rows else 0,
        "product_sales": product_sales
    }

  except Error as exc:
    flash(f"Không thể tải dữ liệu nhân viên: {friendly_error(exc, 'tải dữ liệu nhân viên')}", "error")
    
  return render_template("staff.html", pending_orders=pending_orders, employees=employees,
                           orders=orders, shippers=shippers, revenue_data=revenue_data)


@app.post("/staff/orders/update-status")
def update_order_status():
    conn = cursor = None
    try:
        order_id = required(request.form, "order_id", "mã đơn hàng")
        new_status = required(request.form, "new_status", "trạng thái mới")

        # Quy trình trạng thái 1 chiều (State Machine): Trạng thái hiện tại -> Các trạng thái kế tiếp hợp lệ
        VALID_TRANSITIONS = {
            "Đã xác nhận": ("Đang giao",),
            "Chờ lấy hàng": ("Đang giao",),  # Hỗ trợ cả dữ liệu cũ đang hiển thị là Chờ lấy hàng
            "Đang giao": ("Đã giao", "Trả hàng"),
        }

        conn = get_connection()
        conn.start_transaction()
        cursor = conn.cursor()

        cursor.execute("SELECT TrangThai FROM DON_HANG WHERE MaDH = %s FOR UPDATE", (order_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Không tìm thấy đơn hàng.")

        current_status = row[0]
        allowed_next = VALID_TRANSITIONS.get(current_status, ())

        if not allowed_next:
            raise ValueError(
                f"Đơn {order_id} đang ở trạng thái '{current_status}' (chưa xác nhận hoặc đã kết thúc), "
                "không thể cập nhật thêm."
            )

        if new_status not in allowed_next:
            raise ValueError(
                f"Không thể chuyển từ '{current_status}' sang '{new_status}'. "
                f"Bước tiếp theo hợp lệ chỉ có thể là: {', '.join(allowed_next)}."
            )

        # Cập nhật trạng thái đơn hàng trong DON_HANG
        cursor.execute("UPDATE DON_HANG SET TrangThai = %s WHERE MaDH = %s", (new_status, order_id))

        # Đồng bộ sang bảng VAN_CHUYEN
        if new_status == "Đã giao":
            cursor.execute(
                "UPDATE VAN_CHUYEN SET TrangThaiGiao = 'Đã giao', NgayGiao = NOW() WHERE MaDH = %s",
                (order_id,)
            )
        else:
            cursor.execute(
                "UPDATE VAN_CHUYEN SET TrangThaiGiao = %s WHERE MaDH = %s",
                (new_status, order_id)
            )

        conn.commit()
        flash(f"Đơn {order_id}: Đã tiến triển từ '{current_status}' sang '{new_status}'.", "success")
    except (Error, ValueError) as exc:
        if conn:
            conn.rollback()
        flash(f"Không thể cập nhật trạng thái: {friendly_error(exc, 'cập nhật đơn hàng')}", "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal") + "#manage")

@app.post("/staff/orders/confirm")
def confirm_order():
  conn = cursor = None
  try:
    order_id = required(request.form, "order_id", "mã đơn")
    employee = required(request.form, "employee_cccd", "nhân viên bán hàng")
    conn = get_connection()
    conn.start_transaction()
    cursor = conn.cursor()

    cursor.execute("SELECT CCCD FROM NV_BAN_HANG WHERE CCCD=%s", (employee,))
    if not cursor.fetchone():
      raise ValueError(
          "Nhân viên bán hàng không hợp lệ. Vui lòng chọn lại nhân viên."
      )

    cursor.execute(
        "SELECT TrangThai, PhuongThucTT FROM DON_HANG WHERE MaDH=%s FOR UPDATE",
        (order_id,),
    )
    order = cursor.fetchone()
    if not order or order[0] != "Chờ xác nhận":
      raise ValueError(
          "Đơn hàng không tồn tại hoặc đã được xử lý trước đó. Hãy tải lại danh"
          " sách đơn."
      )

    cursor.execute("SELECT CCCD FROM SHIPPER ORDER BY RAND() LIMIT 1")
    shipper_row = cursor.fetchone()
    if not shipper_row:
      raise ValueError(
          "Hiện chưa có shipper nào trong hệ thống. Không thể xác nhận đơn; vui"
          " lòng bổ sung shipper trước."
      )
    shipper = shipper_row[0]

    # --- KIỂM TRA VÀ TRỪ TỒN KHO TRONG BẢNG LUU_TRU ---
    cursor.execute(
        """
            SELECT ct.MaSP, sp.TenSP, ct.SoLuong
            FROM CT_DON_HANG ct
            JOIN SAN_PHAM sp ON sp.MaSP = ct.MaSP
            WHERE ct.MaDH = %s
        """,
        (order_id,),
    )
    order_items = cursor.fetchall()
    if not order_items:
      raise ValueError("Đơn hàng không có sản phẩm nào để xác nhận.")

    for ma_sp, ten_sp, so_luong_can in order_items:
      # Khóa các dòng tồn kho của sản phẩm này, ưu tiên trừ từ kho còn nhiều hàng nhất
      cursor.execute(
          """
                SELECT MaKho, SoLuongTon
                FROM LUU_TRU
                WHERE MaSP = %s AND SoLuongTon > 0
                ORDER BY SoLuongTon DESC
                FOR UPDATE
            """,
          (ma_sp,),
      )
      stocks = cursor.fetchall()
      tong_ton = sum(row[1] for row in stocks)

      if tong_ton < so_luong_can:
        raise ValueError(
            f"Không thể xác nhận! Sản phẩm '{ten_sp}' ({ma_sp}) chỉ còn"
            f" {tong_ton} trong kho (cần {so_luong_can})."
        )

      con_can_tru = so_luong_can
      for ma_kho, so_luong_ton in stocks:
        if con_can_tru <= 0:
          break
        tru = min(con_can_tru, so_luong_ton)
        cursor.execute(
            """
                    UPDATE LUU_TRU
                    SET SoLuongTon = SoLuongTon - %s
                    WHERE MaSP = %s AND MaKho = %s
                """,
            (tru, ma_sp, ma_kho),
        )
        con_can_tru -= tru
    # ---------------------------------------------------

    cursor.execute(
        """SELECT COALESCE(SUM(ct.SoLuong * sp.DonGia),0)
            FROM CT_DON_HANG ct JOIN SAN_PHAM sp ON sp.MaSP=ct.MaSP WHERE ct.MaDH=%s""",
        (order_id,),
    )
    total = cursor.fetchone()[0] or 0
    cod = total if order[1] == "COD" else 0

    cursor.execute(
        "UPDATE DON_HANG SET TrangThai='Đã xác nhận', CCCD_NVBH=%s WHERE"
        " MaDH=%s AND TrangThai='Chờ xác nhận'",
        (employee, order_id),
    )
    if cursor.rowcount != 1:
      raise ValueError(
          "Đơn hàng vừa được xử lý bởi nhân viên khác. Vui lòng tải lại trang."
      )

    cursor.execute(
        "SELECT MaVC FROM VAN_CHUYEN WHERE MaDH=%s FOR UPDATE", (order_id,)
    )
    existing_shipping = cursor.fetchone()
    if existing_shipping:
      cursor.execute(
          """UPDATE VAN_CHUYEN SET TienCOD=%s, TrangThaiGiao='Chờ lấy hàng',
                NgayGiao=NULL, CCCD_Shipper=%s WHERE MaDH=%s""",
          (cod, shipper, order_id),
      )
    else:
      shipping_id = "VC" + uuid.uuid4().hex[:8].upper()
      cursor.execute(
          """INSERT INTO VAN_CHUYEN
                (MaVC,TienCOD,TrangThaiGiao,NgayGiao,MaDH,CCCD_Shipper)
                VALUES (%s,%s,'Chờ lấy hàng',NULL,%s,%s)""",
          (shipping_id, cod, order_id, shipper),
      )

    conn.commit()
    cursor.execute("SELECT HoTen FROM NGUOI_DUNG WHERE CCCD=%s", (shipper,))
    shipper_name = cursor.fetchone()[0]
    flash(
        f"Đã xác nhận đơn {order_id}, trừ tồn kho và phân công shipper"
        f" {shipper_name}.",
        "success",
    )
  except (Error, ValueError) as exc:
    if conn:
      conn.rollback()
    flash(
        f"Không thể xác nhận đơn: {friendly_error(exc, 'xác nhận đơn hàng')}",
        "error",
    )
  finally:
    if cursor:
      cursor.close()
    if conn:
      conn.close()
  return redirect(url_for("staff_portal") + "#confirm")


@app.route("/staff/invoices")
def invoice():
    invoice_data = None
    order_id = request.args.get("order_id", "").strip()
    if order_id:
        try:
            invoice_data = load_invoice(order_id)
            if not invoice_data:
                flash("Không tìm thấy đơn hàng với mã đã nhập.", "error")
        except Error as exc:
            flash(f"Không thể tạo hóa đơn: {friendly_error(exc, 'tải hóa đơn')}", "error")
    return render_template("invoice.html", invoice=invoice_data, staff_view=True,
                           customer_cccd=None)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
