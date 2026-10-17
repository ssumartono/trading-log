# Tension Flow Trend [BigBeluga] — MT5

Konversi dari Pine Script yang diberikan pengguna. Original © BigBeluga.
Lisensi CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/
Penggunaan nonkomersial, wajib atribusi, distribusi turunan dengan lisensi sama.

## Instalasi
1. MT5 > File > Open Data Folder.
2. Salin TensionFlowTrend_BigBeluga.ex5 ke MQL5/Indicators.
3. Navigator > Indicators > klik kanan Refresh, lalu tarik indikator ke chart.
4. Untuk contoh gambar pilih XAUUSD M1, background gelap, candle hijau/merah.
Tidak perlu mengaktifkan Algo Trading. Indikator tidak mengirim order.
Source MQ5 disertakan agar dapat diperiksa atau diubah di MetaEditor.

## Tampilan dan nilai default
- HMA 50 dengan garis hijau mint saat naik, merah saat turun.
- Pita gradasi transparan: HMA +/- ATR Wilder(14) x 0.5.
- Z-Score: (close - HMA) / standar deviasi populasi jarak close-HMA, 50 bar.
  Ini mengikuti rumus asli, bukan Z-Score yang mengurangi mean pada pembilang.
- START: crossing close/HMA yang searah slope, cooldown 30 bar.
- Kotak hanya dibuat bila slope tidak berubah pada bar sinyal maupun bar sebelumnya.
  Karena itu START tidak selalu disertai kotak.
- Entry close sinyal, SL ATR Wilder(200) x 2, TP 1 kali risiko.
- TP hijau, SL merah; kotak memanjang sampai tersentuh TP atau SL.
- RR Performance: 100 hasil penutupan terakhir; bukan angka tetap dari screenshot.
- Z-Score dan status Strong / Overextended (abs Z > 2) di kanan bawah.
- MaxVisibleTrades 250 membatasi gambar menjadi 500 kotak seperti batas Pine;
  perhitungan statistik tetap mencakup seluruh sinyal pada riwayat yang dimuat.

## Perilaku penting yang dipertahankan dari Pine
ClosedBarSignals=false adalah default agar mengikuti Pine asli: candle berjalan
bisa mengubah sinyal, kotak dan statistik sebelum candle selesai.
Gunakan true untuk sinyal dan penyelesaian hasil hanya pada candle tertutup.
Sinyal baru tetap dihitung mulai close, tetapi high/low seluruh candle entry ikut
diperiksa, sama dengan kode sumber. Jika TP dan SL tersentuh pada candle sama,
TP diprioritaskan dan dihitung menang. Angka panel merupakan simulasi OHLC asli,
bukan pengujian eksekusi order dan tidak memasukkan spread, komisi atau slippage.
Beberapa posisi simulasi dapat aktif bersamaan. ATR baru tersedia setelah 200 bar.
Jika standar deviasi nol, Z ditampilkan N/A. Riwayat dihitung ulang agar perubahan
candle berjalan tidak meninggalkan hasil sementara yang salah.

## Integrasi iCustom (buffer berbasis 0)
0 HMA; 1 indeks warna (0 bullish, 1 bearish); 2 START bullish;
3 START bearish; 4 Z-Score. Sinyal berisi posisi label harga atau EMPTY_VALUE.
Gunakan shift 1 untuk bar tertutup. Buffer warna bukan sinyal transaksi.

## Validasi dan batas
MetaEditor: 0 errors, 0 warnings; compile log disertakan.
Perhitungan weighted moving average diperiksa terhadap rumus langsung.
Belum diuji secara visual pada terminal MT5 atau dibandingkan bar per bar dengan
TradingView. Harga broker, jumlah riwayat, dan sesi berbeda dapat menghasilkan
sinyal/statistik berbeda. Gradasi menggunakan CCanvas MT5 dan mendekati visual
Pine; ukuran font/pixel dapat berbeda menurut resolusi layar.
Indikator tidak mengubah tema chart. Semua objek miliknya dihapus saat dilepas.
