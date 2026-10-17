# EMA/SMA signals + profit protection

Indikator Pine v6, bukan strategy atau eksekutor order. Tidak terhubung dengan posisi broker. Entry referensi adalah Close candle crossover, bukan fill nyata.

- EMA 9 biru / SMA 20 putih; crossover dikonfirmasi saat candle selesai, tanpa filter 3 candle dan tanpa ATR.
- SL awal default 300 ticks. Tick = syminfo.mintick simbol TradingView; jangan samakan otomatis dengan point MT5.
- Saat Close mencapai profit 1R (default), stop digeser ke entry + buffer biaya untuk Buy, entry - buffer untuk Sell. Buffer default 0, jadi biaya belum diperhitungkan; atur sendiri dalam ticks.
- Bila buffer terlalu besar untuk harga saat ini, aktivasi menunggu sampai harga melewati level buffer tersebut.
- Sesudah aktivasi, trailing mengikuti swing low/high terkonfirmasi. Default 2 candle kiri dan 2 kanan; pivot baru diketahui 2 candle setelah titik swing. Hanya pivot setelah entry yang digunakan, tanpa memindahkan sinyal ke masa lalu.
- Stop Buy tidak turun; stop Sell tidak naik. Level baru diperiksa mulai candle berikutnya.
- EXIT berdasarkan Close yang melewati/menyentuh stop sebelumnya, atau crossover berlawanan. Sentuhan wick saja TIDAK menghasilkan EXIT. Harga dapat melewati stop jauh sebelum candle selesai; ini bukan simulasi stop broker intrabar dan tidak menjamin profit terkunci.
- Crossover berlawanan memberi EXIT arah lama sekaligus sinyal entry arah baru. Sesudah exit stop tanpa cross, tunggu crossover baru; tidak entry berulang pada arah sama.
- Tidak ada TP tetap, RR target tetap, atau profit sebagian. 1R adalah ambang aktivasi proteksi, bukan target exit.

Tempel source ke Pine Editor, Save dan Add to chart. Hapus versi indikator lama agar label tidak ganda. Buat ulang alert setelah mengganti kode/input; pilih Once Per Bar Close. Label EXIT dan entry bisa muncul bersamaan ketika reversal. Alert merupakan pemberitahuan, bukan transaksi otomatis.

Verifikasi di TradingView: BUY/SELL hanya saat cross tertutup; proteksi aktif setelah ambang R; swing baru dipakai setelah konfirmasi; trailing tidak mundur; wick tanpa close di luar stop tidak exit; exit stop tidak langsung re-entry. Gunakan chart candle standar untuk harga referensi pasar. Kode belum dikompilasi atau diuji di TradingView.
