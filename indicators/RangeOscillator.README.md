# Range Oscillator MT5

Konversi Pine v6 Range Oscillator oleh Zeiierman. Lisensi CC BY-NC-SA 4.0:
https://creativecommons.org/licenses/by-nc-sa/4.0/ . Atribusi wajib,
penggunaan nonkomersial, dan turunan memakai lisensi yang sama.

## Instalasi

1. MT5 > File > Open Data Folder.
2. Salin RangeOscillator.ex5 ke MQL5/Indicators.
3. Navigator > Indicators > klik kanan > Refresh.
4. Tarik RangeOscillator ke chart. Indikator membuka subwindow sendiri.

## Perhitungan

Default: MinimumRangeLength 50, RangeWidthMultiplier 2,
NumberOfHeatLevels 2, MinimumTouchesPerLevel 1.
MA memakai bobot abs(close - close sebelumnya) / close sebelumnya.
Oscillator = 100 * (close - MA) / (ATR * multiplier).
ATR memakai Wilder RMA 2000, dengan RMA 200 sebelum tersedia 2000 bar.
Garis referensi +100, 0, -100; skala otomatis memungkinkan breakout melampaui batas.
Heatmap menggunakan 100 bar terakhir dan level terdekat; pergantian tren biru,
breakout atas hijau terang, breakout bawah merah. Candle berjalan dapat berubah.
Original memakai warna weak di kedua ujung gradasi heatmap; ini dipertahankan.
Variabel inRange original tidak memengaruhi hasil plot dan tidak diperlukan.

## Tampilan dan batas validasi

Versi 1.10 menambahkan panah dan teks Buy/Sell di chart utama (window 0).
Buy: oscillator sebelumnya <= +100 dan sekarang > +100.
Sell: oscillator sebelumnya >= -100 dan sekarang < -100.
Ini aturan sinyal tambahan dari kondisi breakout, bukan sinyal yang sudah ada
di Pine asli. Tanda hanya muncul pada penembusan, bukan setiap candle di luar batas.
ShowBuySell mengatur tanda; ClosedBarSignals=true menunggu candle selesai.
ClosedBarSignals=false mengaktifkan tanda intrabar yang dapat muncul/hilang.
SignalOffsetPoints (default 30) mengatur jarak dari low/high dalam point simbol.
Osilator tetap di subwindow. Tanda milik masing-masing instance dibersihkan saat
indikator dilepas atau parameter diubah. Tidak menambahkan eksekusi order.

Transparansi garis didekati dengan 11 tingkat campuran warna background.
Area gradasi Pine didekati histogram redup; ShowShading menonaktifkannya.
Pasang ulang indikator setelah mengganti background untuk menyegarkan campuran warna.
Minimal 200 bar dan MinimumRangeLength+1 bar diperlukan. Harga konstan tanpa
bobot perubahan menghasilkan nilai kosong, mengikuti MA yang undefined pada Pine.
Perbedaan riwayat atau feed broker bisa mengubah hasil dibanding TradingView.

Buffer iCustom: 0 shading, 1 indeks warna shading, 2 oscillator,
3 indeks warna oscillator. Gunakan buffer 2 shift 1 untuk candle selesai.

Compile MetaEditor: 0 errors, 0 warnings. Belum diuji visual pada chart atau
dibandingkan bar per bar dengan TradingView pada data OHLC identik.
Tidak membuka order.
