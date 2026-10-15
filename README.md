# TradingLog

Aplikasi jurnal trading lokal dengan SQLite, integrasi MetaTrader 5, dan tampilan bergaya Outlook. Mendukung desktop, tablet, mobile, serta tema Light/Dark.

## Fitur

- Live Chart sebagai halaman awal: candlestick, volume, timeframe M1–D1, pembaruan setiap 5 detik dan posisi terbuka. Menggunakan TradingView Lightweight Charts.
- Dashboard per akun, waterfall saldo, filter periode, dan riwayat transaksi.
- Kalender trading hingga jam, tabel log, sort dan pagination.
- Pengaturan broker, tes koneksi, sinkronisasi MT5 dan riwayat Deposit/Withdraw.
- Analisa Performance per log/deal: profit factor, rasio log profit, waterfall, heatmap dan perbandingan kelompok.
- Catatan Harian, Memo, Event dan Lesson Learned dengan mailbox dan editor panel kanan.
- AI Assistant untuk draf catatan dan AI Trader Assistant dengan konteks market opsional.
- Indikator MT5 tambahan pada folder `indicators`; lihat panduan masing-masing.

## Menjalankan di Windows

Siapkan Python yang kompatibel dengan paket MetaTrader5 dan terminal MT5 desktop.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python server.py
```

Buka **http://127.0.0.1:3000/**. Server hanya mendengarkan localhost. Belum ada autentikasi pengguna atau konfigurasi deployment publik; ini aplikasi lokal.

## Konfigurasi akun MT5

1. Login akun pada terminal MT5 dan tampilkan simbol di Market Watch.
2. Di aplikasi, buka **Pengaturan → Tambah akun broker baru**.
3. Isi nomor akun, server, lokasi terminal dan tanggal mulai impor.
4. Gunakan **Tes koneksi & daftarkan**, lalu **Sync sekarang**.
5. Pilih akun pada navigasi. Terminal harus aktif pada akun yang sama saat mengambil data atau sinkronisasi.

Satu terminal menggunakan satu akun aktif. Data dicatat per deal, sehingga Entry dan Exit tetap menjadi log terpisah. Posisi Exit ditampilkan memakai arah posisi asal; arah eksekusi juga tersedia di detail. Timestamp mentah MT5 dapat mengikuti offset broker; periksa waktu terminal saat membandingkan candle dan riwayat.

## AI opsional

Di **Pengaturan → Setup API Key**, pilih AI Platform, URL, Model Name dan API Key. OpenAI memakai endpoint `/v1/responses`; OpenAI Compatible memakai endpoint `/chat/completions`.

Konfigurasi disimpan di memori server dan hilang setelah restart. Alternatif untuk OpenAI: environment `OPENAI_API_KEY` dan `OPENAI_MODEL`. Jangan memasukkan key ke source control. AI hanya menghasilkan draf/diskusi; tidak mengeksekusi order. Konteks market/log hanya dikirim ke penyedia AI ketika opsi tersebut dipilih.

## Data dan pengujian

SQLite dibuat otomatis pada `data/tradinglog.sqlite3`. Folder data, API key, kredensial dan konfigurasi akun pribadi tidak disertakan dalam repository. Cadangkan database secara terpisah. Field hasil MT5 mengikuti sinkronisasi; strategi, indikator dan catatan dapat diedit manual.

```powershell
python -m unittest discover -p "test_*.py"
```

Pengujian memakai data buatan/database sementara; bukan transaksi sungguhan. Fitur Trading Plan tidak disertakan karena telah dibatalkan.

## Komponen pihak ketiga

TradingView Lightweight Charts™ 5.2.0 disertakan pada `mockup/vendor/` dengan LICENSE dan NOTICE aslinya. Copyright (c) 2025 TradingView, Inc. https://www.tradingview.com/

Lihat komentar dan panduan dalam `indicators/` untuk asal-usul dan ketentuan kode indikator masing-masing.
