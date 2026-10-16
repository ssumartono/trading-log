# Zona waktu tampilan global

Pengaturan → Pengaturan Global Aplikasi menyediakan WIB (default), Waktu Broker, dan UTC. Preferensi tersimpan di SQLite pada tabel app_preferences, berlaku untuk semua pengguna workspace setelah memuat ulang aplikasi. Pengguna dengan settings.manage dapat menyimpan; data.view dapat membaca.

Pilihan mengatur sumbu waktu, crosshair, tick dan waktu pembacaan Live Chart, waktu snapshot AI Trader Assistant, serta status sinkronisasi. Waktu Broker menggunakan offset menit per akun, terpisah dari timestampMode/serverUtcOffsetMinutes pada konfigurasi integrasi. Tanpa offset, tampilan jatuh ke UTC dengan label peringatan. Offset broker perlu diperiksa terhadap chart terminal dan perubahan musim.

Tanggal/jam jurnal manual, kalender, filter periode, dan laporan tetap WIB serta diberi label WIB. Pengaturan tampilan ini tidak menggeser timestamp data MT5, waktu input jurnal, harga, atau batas candle. Uji pergantian tanggal dilakukan untuk WIB dan UTC; offset per akun diuji secara terpisah.

Uji: python -m unittest test_app_preferences test_auth_http -v; node mockup/check-app-time.cjs.
