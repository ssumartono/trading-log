# Auto Fibonacci Retracement — MT5

Implementasi mandiri berdasarkan gambar dan deskripsi pengguna. Bukan salinan
algoritma TradingView asli karena source aslinya tidak disediakan. Pemilihan
swing dan nilai level dapat berbeda dari indikator pada gambar.

## Pemasangan

1. MT5 > File > Open Data Folder.
2. Salin AutoFibonacciRetracement.ex5 ke MQL5/Indicators.
3. Navigator > Indicators > klik kanan > Refresh.
4. Tarik AutoFibonacciRetracement ke chart simbol dan timeframe pilihan.

Source .mq5 disertakan untuk diedit/compile melalui MetaEditor MT5.
Indikator tidak membuka transaksi dan tidak memerlukan DLL.

## Tampilan

- 23,6% merah, 38,2% hijau muda, 50% hijau, 61,8% teal, 78,6% biru.
- Label menampilkan rasio dan harga sesuai digit simbol broker.
- Garis batas high merah dan low hijau bertitik, memanjang ke kanan.
- Garis putus-putus menghubungkan awal dan akhir swing.
- Label beserta garis pendek ditempatkan relatif terhadap lebar chart,
  seperti contoh gambar; mengikuti perubahan skala harga dan ukuran chart.
- Level di luar rentang harga chart tidak menampilkan label. Indikator tidak
  mengubah tema, skala, atau warna candle chart pengguna.
- FullLevelRays=true menambahkan garis horizontal panjang pada level tengah.
- Show786, ShowSwingLine, ShowBoundaryRays mengatur elemen terkait.
- LabelPositionPercent default 65; geser ke kiri bila label terpotong pada
  chart sempit. FontSize default 10.

## Pemilihan swing

| SwingStyle | ATR period | Pembalikan minimum | EMA filter |
|---|---:|---:|---:|
| SCALPING | 14 | 1,5 × ATR | 13 |
| TREND_TRADING (default) | 14 | 3 × ATR | 34 |
| SWING_TRADING | 14 | 5 × ATR | 89 |
| CUSTOM | CustomATRPeriod | CustomReversalATR × ATR | CustomEMAPeriod |

Harga close harus berbalik dari ekstrem setidaknya sebesar ambang ATR.
Jika UseTrendFilter=true, close juga harus di bawah EMA untuk beralih turun,
atau di atas EMA untuk beralih naik. Pembalikan hanya diproses pada candle
selesai yang waktunya setelah candle ekstrem; candle yang sekaligus membuat
ekstrem baru tidak mengonfirmasi pembalikan. Ini menghindari asumsi urutan
high/low intrabar dari data OHLC.

Pada uptrend, awal swing adalah low dan ekstrem aktif adalah high.
Pada downtrend, awal adalah high dan ekstrem aktif adalah low.
Level dihitung sebagai: akhir + (awal − akhir) × rasio.
Jadi 0% di akhir pergerakan dan 100% di awal pergerakan; pada contoh downtrend,
23,6% berada dekat swing low dan 78,6% lebih dekat swing high.

LiveSwing=true memperbarui ekstrem aktif pada setiap tick jika high/low baru
tercapai. Semua level aktif dapat bergeser (repaint). False membatasi pemilihan
ekstrem pada candle selesai, tetapi level tetap dapat bergeser pada candle
berikutnya. Ini bukan indikator swing terkunci/non-repaint.

HistoryBars default 3000 membatasi replay untuk efisiensi. ATR menggunakan
Wilder smoothing dan EMA dihitung dari awal jendela riwayat dengan periode
pemanasan. Saat jendela bergeser atau data broker berubah, hasil dapat berubah.
HistoryBars harus setidaknya periode terbesar + 10. Tunggu riwayat dan gerakan
yang cukup jika belum muncul swing; tidak ada pasangan swing buatan saat data
belum memenuhi syarat. Setting lebih besar biasanya menghasilkan swing lebih
panjang, tetapi hasil bergantung pada pergerakan harga.

## Validasi

Dikompilasi dengan MetaEditor MT5: 0 errors, 0 warnings.
Belum diuji visual pada chart MT5 atau dibandingkan dengan indikator TradingView
asli. Tidak ada klaim bahwa swing yang dipilih selalu benar atau menghasilkan
keuntungan. Tidak tersedia buffer iCustom; hasil digambar sebagai objek chart.

Referensi API objek MT5:
https://www.mql5.com/en/docs/objects/objectcreate
