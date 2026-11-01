-- HE THONG BAN HANG VA VAN CHUYEN - MySQL 8.0.16+
-- Da bo sung rang buoc thuoc tinh, khoa ngoai va nghiep vu.
-- Luu y:
--   * CHECK duoc thuc thi tu MySQL 8.0.16 tro len.
--   * Cac gia tri ENUM/ CHECK la quy uoc nghiep vu mau; dieu chinh
--     neu ERD/quy dinh thuc te cua ban dung bo gia tri khac.
--   * Khong the chi dung FK/CHECK de dam bao ton kho du khi dat hang
--     hoac dong bo vai tro NGUOI_DUNG voi cac bang vai tro con.
-- =============================================================

CREATE DATABASE IF NOT EXISTS quan_ly_ban_hang_va_van_chuyen
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE quan_ly_ban_hang_va_van_chuyen;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS VAN_CHUYEN;
DROP TABLE IF EXISTS LUU_TRU;
DROP TABLE IF EXISTS CT_DON_HANG;
DROP TABLE IF EXISTS DON_HANG;
DROP TABLE IF EXISTS SHIPPER;
DROP TABLE IF EXISTS NV_KHO;
DROP TABLE IF EXISTS NV_BAN_HANG;
DROP TABLE IF EXISTS KHACH_HANG;
DROP TABLE IF EXISTS SAN_PHAM;
DROP TABLE IF EXISTS KHO_HANG;
DROP TABLE IF EXISTS NGUOI_DUNG_SDT;
DROP TABLE IF EXISTS NGUOI_DUNG_EMAIL;
DROP TABLE IF EXISTS NGUOI_DUNG_VAITRO;
DROP TABLE IF EXISTS NGUOI_DUNG;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------- Nguoi dung ----------
CREATE TABLE NGUOI_DUNG (
    CCCD       CHAR(12) PRIMARY KEY NOT NULL,
    HoTen      NVARCHAR(100) NOT NULL,
    NgaySinh   DATE NULL,
    GioiTinh   NVARCHAR(10) NULL
);


CREATE TABLE NGUOI_DUNG_VAITRO (
    CCCD   CHAR(12) NOT NULL,
    VaiTro NVARCHAR(30) NOT NULL,
    PRIMARY KEY (CCCD, VaiTro),
    CONSTRAINT FK_VAITRO_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
);

-- Email va SDT la thuoc tinh da tri.
CREATE TABLE NGUOI_DUNG_EMAIL (
    CCCD  CHAR(12) NOT NULL,
    Email VARCHAR(100) UNIQUE NOT NULL,
    PRIMARY KEY (CCCD, Email),
    CONSTRAINT FK_EMAIL_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE NGUOI_DUNG_SDT (
    CCCD CHAR(12) UNIQUE NOT NULL,
    SDT  VARCHAR(15) UNIQUE NOT NULL,
    PRIMARY KEY (CCCD, SDT),
    CONSTRAINT FK_SDT_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
);

-- ---------- Kho hang va san pham ----------
CREATE TABLE KHO_HANG (
    MaKho     VARCHAR(10) PRIMARY KEY NOT NULL,
    TenKho    NVARCHAR(100) NOT NULL,
    DiaChiKho NVARCHAR(255) NOT NULL,
    SDT       VARCHAR(15) NULL
);

CREATE TABLE SAN_PHAM (
    MaSP    VARCHAR(10) PRIMARY KEY NOT NULL,
    TenSP   VARCHAR(150) NOT NULL,
    DonGia  DECIMAL(15,2) NOT NULL,
    CONSTRAINT SAN_PHAM_CHECK CHECK (DonGia >= 0)
);

-- ---------- Cac vai tro con cua NGUOI_DUNG ----------
-- CCCD vua la PK vua la FK: moi dong vai tro con phai co nguoi dung goc.
CREATE TABLE KHACH_HANG (
    CCCD   CHAR(12) PRIMARY KEY NOT NULL,
    DiaChi NVARCHAR(255) NULL,
    CONSTRAINT FK_KHACH_HANG_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE NV_BAN_HANG (
    CCCD       CHAR(12) PRIMARY KEY NOT NULL,
    NgayVaoLam DATE NOT NULL,
    CONSTRAINT FK_NV_BAN_HANG_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
    -- Kiem tra NgayVaoLam khong o tuong lai tai tang ung dung/trigger.
);

CREATE TABLE NV_KHO (
    CCCD       CHAR(12) PRIMARY KEY NOT NULL,
    NgayVaoLam DATE NOT NULL,
    MaKho      VARCHAR(10) NOT NULL,

    CONSTRAINT FK_NV_KHO_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT FK_NV_KHO_KHO_HANG FOREIGN KEY (MaKho) REFERENCES KHO_HANG (MaKho) ON UPDATE CASCADE ON DELETE RESTRICT
    -- Kiem tra NgayVaoLam khong o tuong lai tai tang ung dung/trigger.
);

CREATE TABLE SHIPPER (
    CCCD   CHAR(12) PRIMARY KEY NOT NULL,
    KhuVuc NVARCHAR(100) NOT NULL,
    BienSo VARCHAR(15) NULL,
    LoaiXe NVARCHAR(50) NULL,
    CONSTRAINT FK_SHIPPER_NGUOI_DUNG FOREIGN KEY (CCCD) REFERENCES NGUOI_DUNG (CCCD) ON UPDATE CASCADE ON DELETE CASCADE
);

-- ---------- Don hang ----------
CREATE TABLE DON_HANG (
    MaDH           VARCHAR(10) PRIMARY KEY NOT NULL,
    NgayDat        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    TrangThai      NVARCHAR(255) NULL,
    GhiChu         NVARCHAR(255) NULL,
    NgayTT         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PhuongThucTT   NVARCHAR(30) NULL,
    TenNguoiNhan   NVARCHAR(100) NOT NULL,
    SDTNguoiNhan   NVARCHAR(15) NOT NULL,
    DiaChiNhanHang NVARCHAR(255) NOT NULL,
    CCCD_KH        CHAR(12) NOT NULL,
    CCCD_NVBH      CHAR(12) NULL,

    CONSTRAINT FK_DON_HANG_KH FOREIGN KEY (CCCD_KH) REFERENCES KHACH_HANG (CCCD) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_DON_HANG_NV_BAN_HANG FOREIGN KEY (CCCD_NVBH) REFERENCES NV_BAN_HANG (CCCD) ON UPDATE CASCADE ON DELETE SET NULL
);

-- Moi san pham xuat hien toi da mot lan trong mot don hang.
CREATE TABLE CT_DON_HANG (
    MaDH    VARCHAR(10) NOT NULL,
    MaSP    VARCHAR(10) NOT NULL,
    SoLuong INT NOT NULL,
    PRIMARY KEY (MaDH, MaSP),
    CONSTRAINT CK_CT_DON_HANG_SOLUONG CHECK (SoLuong > 0),
    CONSTRAINT FK_CT_DON_HANG_DH FOREIGN KEY (MaDH) REFERENCES DON_HANG (MaDH) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT FK_CT_DON_HANG_SP FOREIGN KEY (MaSP) REFERENCES SAN_PHAM (MaSP) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Bang ton kho: mot san pham co the nam o nhieu kho.
CREATE TABLE LUU_TRU (
    MaSP       VARCHAR(10) NOT NULL,
    MaKho      VARCHAR(10) NOT NULL,
    SoLuongTon INT NOT NULL CHECK (SoLuongTon >= 0) DEFAULT 0,

    PRIMARY KEY (MaSP, MaKho),
    CONSTRAINT FK_LUU_TRU_SAN_PHAM FOREIGN KEY (MaSP) REFERENCES SAN_PHAM (MaSP) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_LUU_TRU_KHO_HANG FOREIGN KEY (MaKho) REFERENCES KHO_HANG (MaKho) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- Moi don hang co toi da mot van chuyen (theo mo hinh 1-1 hien tai).
-- MaDH de NULL neu van don chua duoc gan don hang.
CREATE TABLE VAN_CHUYEN (
    MaVC          VARCHAR(10) PRIMARY KEY NOT NULL,
    TienCOD       DECIMAL(15,2) NOT NULL DEFAULT 0,
    TrangThaiGiao NVARCHAR(30) NOT NULL,
    NgayGiao      DATETIME NULL,
    MaDH          VARCHAR(10) UNIQUE NULL,
    CCCD_Shipper  CHAR(12) NULL,
    CONSTRAINT CHECK_COD CHECK (TienCOD >= 0),
    CONSTRAINT FK_VAN_CHUYEN_DH FOREIGN KEY (MaDH) REFERENCES DON_HANG (MaDH) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT FK_VAN_CHUYEN FOREIGN KEY (CCCD_Shipper) REFERENCES SHIPPER (CCCD) ON UPDATE CASCADE ON DELETE SET NULL
);

-- =============================================================
-- NHUNG QUY TAC CAN XU LY THEM O TANG UNG DUNG / TRANSACTION:
-- 1. Don hang phai co it nhat mot CT_DON_HANG.
-- 2. Khi xac nhan/xuat don: khoa ton kho, kiem tra SoLuongTon du,
--    tru ton kho va cap nhat trang thai trong cung mot transaction.
-- 3. Tong tien don hang = SUM(SoLuong * DonGia). Neu can luu gia tai
--    thoi diem dat hang, them DonGiaTaiThoiDiem vao CT_DON_HANG;
--    khong nen chi lay DonGia hien tai cua SAN_PHAM de in hoa don cu.
-- 4. Dam bao dong bo NGUOI_DUNG_VAITRO voi cac bang vai tro con
--    (KHACH_HANG/NV_BAN_HANG/NV_KHO/SHIPPER) bang logic ung dung
--    hoac trigger. FK hien tai khong tu dong kiem tra su khop ay.
-- =============================================================
-- DU LIEU BAN DAU - quan_ly_ban_hang_va_van_chuyen (MySQL 8.0.16+)
-- Chay SAU khi da chay create_table.sql.
-- CCCD, SDT, email la du lieu gia lap.


-- ---------- NGUOI_DUNG (14 nguoi) ----------
INSERT INTO NGUOI_DUNG (CCCD, HoTen, NgaySinh, GioiTinh) VALUES
-- Khach hang
('001201000001', 'Nguyễn Văn An',    '1995-03-12', 'Nam'),
('001201000002', 'Trần Thị Bích',    '1998-07-25', 'Nữ'),
('001201000003', 'Lê Hoàng Cường',   '1990-11-02', 'Nam'),
('001201000004', 'Phạm Thu Dung',    '2001-01-18', 'Nữ'),
('001201000005', 'Võ Minh Em',       '1993-09-30', 'Nam'),
-- Nhan vien ban hang
('001201000006', 'Đặng Quốc Phong',  '1992-05-14', 'Nam'),
('001201000007', 'Bùi Thanh Giang',  '1996-12-08', 'Nữ'),
('001201000008', 'Hoàng Gia Huy',    '1994-02-21', 'Nam'),
-- Nhan vien kho
('001201000009', 'Ngô Thị Lan',      '1991-08-16', 'Nữ'),
('001201000010', 'Đỗ Văn Khải',      '1989-04-03', 'Nam'),
('001201000011', 'Lý Mỹ Linh',       '1997-10-27', 'Nữ'),
-- Shipper
('001201000012', 'Trịnh Văn Minh',   '1995-06-09', 'Nam'),
('001201000013', 'Phan Đức Nam',     '1993-12-19', 'Nam'),
('001201000014', 'Vũ Tuấn Oanh',     '1999-03-05', 'Nam');

-- ---------- NGUOI_DUNG_VAITRO ----------
INSERT INTO NGUOI_DUNG_VAITRO (CCCD, VaiTro) VALUES
('001201000001', 'Khách hàng'),
('001201000002', 'Khách hàng'),
('001201000003', 'Khách hàng'),
('001201000004', 'Khách hàng'),
('001201000005', 'Khách hàng'),
('001201000006', 'NV bán hàng'),
('001201000007', 'NV bán hàng'),
('001201000008', 'NV bán hàng'),
('001201000009', 'NV kho'),
('001201000010', 'NV kho'),
('001201000011', 'NV kho'),
('001201000012', 'Shipper'),
('001201000013', 'Shipper'),
('001201000014', 'Shipper');

-- ---------- NGUOI_DUNG_EMAIL (da tri: 001201000001 co 2 email) ----------
INSERT INTO NGUOI_DUNG_EMAIL (CCCD, Email) VALUES
('001201000001', 'an.nguyen@example.com'),
('001201000001', 'an.nguyen.work@example.com'),
('001201000002', 'bich.tran@example.com'),
('001201000003', 'cuong.le@example.com'),
('001201000004', 'dung.pham@example.com'),
('001201000005', 'em.vo@example.com'),
('001201000006', 'phong.dang@example.com'),
('001201000007', 'giang.bui@example.com'),
('001201000008', 'huy.hoang@example.com'),
('001201000009', 'lan.ngo@example.com'),
('001201000010', 'khai.do@example.com'),
('001201000011', 'linh.ly@example.com'),
('001201000012', 'minh.trinh@example.com'),
('001201000013', 'nam.phan@example.com'),
('001201000014', 'oanh.vu@example.com');

-- ---------- NGUOI_DUNG_SDT (da tri: 001201000002 co 2 so) ----------
INSERT INTO NGUOI_DUNG_SDT (CCCD, SDT) VALUES
('001201000001', '0901000001'),
('001201000002', '0901000002'),
('001201000003', '0901000003'),
('001201000004', '0901000004'),
('001201000005', '0901000005'),
('001201000006', '0902000006'),
('001201000007', '0902000007'),
('001201000008', '0902000008'),
('001201000009', '0903000009'),
('001201000010', '0903000010'),
('001201000011', '0903000011'),
('001201000012', '0904000012'),
('001201000013', '0904000013'),
('001201000014', '0904000014');

-- ---------- KHO_HANG ----------
INSERT INTO KHO_HANG (MaKho, TenKho, DiaChiKho, SDT) VALUES
('K01', 'Kho Hà Nội',     '25 Phạm Hùng, Nam Từ Liêm, Hà Nội',         '02438000001'),
('K02', 'Kho Đà Nẵng',    '88 Nguyễn Văn Linh, Hải Châu, Đà Nẵng',     '02363000002'),
('K03', 'Kho TP.HCM',     '120 Quốc lộ 13, Thủ Đức, TP. Hồ Chí Minh',  '02838000003');

-- ---------- SAN_PHAM ----------
INSERT INTO SAN_PHAM (MaSP, TenSP, DonGia) VALUES
('SP01', 'Tai nghe Bluetooth TWS',   590000),
('SP02', 'Chuột không dây',          220000),
('SP03', 'Bàn phím cơ',              950000),
('SP04', 'Sạc nhanh 20W',            180000),
('SP05', 'Cáp USB-C 1m',              60000),
('SP06', 'Loa Bluetooth mini',       450000),
('SP07', 'Ốp lưng điện thoại',        80000),
('SP08', 'Pin dự phòng 10000mAh',    350000),
('SP09', 'Webcam Full HD',           520000),
('SP10', 'Đèn bàn LED',              270000);

-- ---------- Cac bang vai tro con ----------
INSERT INTO KHACH_HANG (CCCD, DiaChi) VALUES
('001201000001', '12 Láng Hạ, Đống Đa, Hà Nội'),
('001201000002', '45 Lê Duẩn, Hải Châu, Đà Nẵng'),
('001201000003', '78 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh'),
('001201000004', '9 Trần Phú, Hà Đông, Hà Nội'),
('001201000005', '33 Điện Biên Phủ, Bình Thạnh, TP. Hồ Chí Minh');

INSERT INTO NV_BAN_HANG (CCCD, NgayVaoLam) VALUES
('001201000006', '2020-02-10'),
('001201000007', '2021-06-01'),
('001201000008', '2022-09-15');

INSERT INTO NV_KHO (CCCD, NgayVaoLam, MaKho) VALUES
('001201000009', '2019-11-05', 'K01'),
('001201000010', '2020-08-20', 'K02'),
('001201000011', '2023-01-09', 'K03');

INSERT INTO SHIPPER (CCCD, KhuVuc, BienSo, LoaiXe) VALUES
('001201000012', 'Hà Nội',     '29A-123.45', 'Xe máy'),
('001201000013', 'Đà Nẵng',    '43B-678.90', 'Xe máy'),
('001201000014', 'TP. Hồ Chí Minh', '59C-246.81', 'Xe tải nhỏ');

-- ---------- LUU_TRU (ton kho) ----------
INSERT INTO LUU_TRU (MaSP, MaKho, SoLuongTon) VALUES
('SP01', 'K01', 50), ('SP01', 'K03', 30),
('SP02', 'K01', 80), ('SP02', 'K02', 40),
('SP03', 'K01', 20), ('SP03', 'K03', 15),
('SP04', 'K01', 100), ('SP04', 'K02', 60), ('SP04', 'K03', 70),
('SP05', 'K01', 200), ('SP05', 'K02', 120), ('SP05', 'K03', 150),
('SP06', 'K02', 35), ('SP06', 'K03', 25),
('SP07', 'K01', 90), ('SP07', 'K03', 110),
('SP08', 'K01', 45), ('SP08', 'K02', 30),
('SP09', 'K03', 18),
('SP10', 'K02', 22), ('SP10', 'K03', 28);

-- ---------- DON_HANG ----------
-- NgayTT: ngay thanh toan thuc te (chuyen khoan/vi) hoac ngay du kien thu COD.
INSERT INTO DON_HANG
    (MaDH, NgayDat, TrangThai, GhiChu, NgayTT, PhuongThucTT,
     TenNguoiNhan, SDTNguoiNhan, DiaChiNhanHang, CCCD_KH, CCCD_NVBH) VALUES
('DH001', '2026-10-01 09:15:00', 'Đã giao',        'Giao giờ hành chính',  '2026-10-03 14:20:00', 'COD',
 'Nguyễn Văn An',  '0901000001', '12 Láng Hạ, Đống Đa, Hà Nội',               '001201000001', '001201000006'),
('DH002', '2026-10-05 10:30:00', 'Đã giao',        NULL,                   '2026-10-05 10:35:00', 'Chuyển khoản',
 'Trần Thị Bích',  '0901000002', '45 Lê Duẩn, Hải Châu, Đà Nẵng',             '001201000002', '001201000007'),
('DH003', '2026-10-25 15:45:00', 'Đang giao',      'Gọi trước khi giao',   '2026-10-31 17:00:00', 'COD',
 'Lê Hoàng Cường', '0901000003', '78 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh',    '001201000003', '001201000006'),
('DH005', '2026-10-20 19:10:00', 'Giao thất bại',  'Khách không nhận máy', '2026-10-23 12:00:00', 'COD',
 'Phạm Thu Dung',  '0901000004', '9 Trần Phú, Hà Đông, Hà Nội',               '001201000004', '001201000007'),
('DH006', '2026-10-30 11:00:00', 'Chờ xác nhận',   'Đặt online',           '2026-10-30 11:02:00', 'Chuyển khoản',
 'Võ Minh Em',     '0901000005', '33 Điện Biên Phủ, Bình Thạnh, TP. Hồ Chí Minh', '001201000005', NULL);

-- ---------- CT_DON_HANG ----------
INSERT INTO CT_DON_HANG (MaDH, MaSP, SoLuong) VALUES
('DH001', 'SP01', 1), ('DH001', 'SP05', 2),
('DH002', 'SP03', 1), ('DH002', 'SP02', 1),
('DH003', 'SP08', 2), ('DH003', 'SP04', 1),
('DH005', 'SP09', 1), ('DH005', 'SP10', 2),
('DH006', 'SP05', 5), ('DH006', 'SP04', 2);

-- ---------- VAN_CHUYEN ----------
-- TienCOD = tong tien don neu thanh toan COD, nguoc lai = 0.
-- DH006 chua xac nhan nen chua co van don.
INSERT INTO VAN_CHUYEN (MaVC, TienCOD, TrangThaiGiao, NgayGiao, MaDH, CCCD_Shipper) VALUES
('VC001',  710000, 'Đã giao',        '2026-10-03 14:20:00', 'DH001', '001201000012'),
('VC002',       0, 'Đã giao',        '2026-10-07 16:05:00', 'DH002', '001201000013'),
('VC003',  880000, 'Đang giao',      NULL,                  'DH003', '001201000014'),
('VC005', 1060000, 'Giao thất bại',  NULL,                  'DH005', '001201000012');
