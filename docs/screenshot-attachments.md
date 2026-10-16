# Lampiran screenshot

- Live Chart: klik kanan pada chart untuk menangkap chart, mengunggah gambar, atau membuka galeri akun. Tombol Tangkap chart dan Unggah gambar juga tersedia di panel kanan untuk tablet/mobile. Tangkapan berisi area chart, bukan seluruh layar. Simbol dan timeframe dicatat saat penyimpanan.
- Detail Log Trading: galeri terkait ID log berada di bawah detail transaksi. Lampiran tersedia juga untuk log MT5 yang data transaksinya terkunci.
- Catatan & Memo: galeri tersedia pada detail dan editor catatan tersimpan. Simpan catatan baru terlebih dahulu sebelum menambahkan gambar.
- Analisa Performance: tombol Lampiran pada tabel log sumber membuka galeri transaksi. Detail Profit (Max) / Loss (Max) juga menampilkan galeri yang sama.

Format PNG, JPEG, WebP; maksimal 5 MB/gambar dan 20 gambar per log/catatan/akun chart. Galeri menampilkan lima gambar per halaman, dengan pratinjau besar, edit keterangan, dan hapus.

Metadata dan byte gambar disimpan dalam tabel SQLite `attachments`, terpisah dari state sinkronisasi MT5. Backup/Restore SQLite mencakup gambar. Cadangan lama tanpa tabel attachments tetap dapat direstore; galeri kembali kosong sesuai isi cadangan. Batas ukuran berkas backup tetap 64 MB.

Akses baca mengikuti data.view (log), notes.view (memo), market.view (chart). Perubahan memerlukan logs.edit (log/chart) atau notes.edit (memo), diperiksa server. Tindakan dicatat di Audit Trail. Gambar tidak dikirim ke AI Assistant secara otomatis. Penghapusan log/broker menghapus lampiran terkait untuk mencegah keterkaitan pada ID yang dipakai ulang.

Pengujian: `python -m unittest test_attachments test_backup_audit test_backup_http` dan pemeriksaan sintaks JavaScript. Database tes terpisah dari data pengguna.
