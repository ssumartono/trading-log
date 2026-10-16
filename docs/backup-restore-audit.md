# Backup / Restore dan Audit Trail

Menu Administrator menyediakan **Backup / Restore** dan **Audit Trail**. Hak akses terpisah `backup.manage` dan `audit.view` tersedia dalam Rules & Access; Administrator selalu memiliki keduanya. Trader dan Viewer tidak mendapat akses bawaan.

## Cadangan

- Buat backup sekarang mengambil snapshot konsisten SQLite, termasuk WAL yang sudah dikomit. Berkas disimpan di `data/backups/` dan dapat diunduh. Maksimal ukuran yang divalidasi adalah 64 MB.
- Unggah menerima berkas SQLite, bukan arsip ZIP. Nama berkas server dibuat otomatis. Validasi memeriksa integritas SQLite, tabel/kolom aplikasi, JSON, serta Administrator aktif dengan hash password valid. Cadangan dari struktur aplikasi berbeda ditolak.
- Backup mencakup log trading, broker, mutasi dana, riwayat MT5 dan sinkronisasi, checkpoint saldo, memo, percakapan AI, strategi, pengguna/role, pengaturan global, dan audit. Sesi login dibuang dari salinan.
- API key dan konfigurasi AI terenkripsi di `data/ai-settings.dpapi` tidak termasuk snapshot SQLite. Restore mempertahankan berkas key aktif. Cadangkan berkas ini secara terpisah jika diperlukan; DPAPI tetap terikat pada akun Windows asal.
- Berkas backup mencakup data pribadi dan hash password pengguna. Unduh hanya melalui endpoint yang memeriksa hak akses; direktori data tidak dilayani sebagai direktori publik.

## Pemulihan

Pilih **Validasi / Restore** untuk melihat jumlah data dan SHA-256. Ketik `RESTORE` sebagai konfirmasi untuk cadangan tersebut. Hash diperiksa kembali saat tindakan dijalankan. Aplikasi tidak menjalankan skema atau trigger dari berkas unggahan; hanya menyalin data tabel aplikasi yang tervalidasi.

Sebelum mengubah data, aplikasi membuat snapshot `before-restore-…`. Penyalinan data berlangsung dalam satu transaksi: kesalahan membatalkan seluruh pemulihan. Riwayat audit aktif dipertahankan dan event audit cadangan digabung berdasarkan ID unik. Restore dicatat sebagai satu tindakan, bukan ribuan edit tiruan.

Semua sesi login dicabut setelah restore. Login ulang menggunakan akun dan password yang ada pada cadangan. Sinkronisasi otomatis/integrasi MT5 dijeda; periksa akun terminal serta Pengaturan sebelum mengaktifkannya kembali. Permintaan edit lama yang sedang berjalan ditolak setelah workspace direstore.

## Audit

Pencatatan dimulai ketika fitur diaktifkan; riwayat lama tidak direkonstruksi. Audit mencakup perubahan log/dana/broker/integrasi, memo, strategi, pengguna/role, pengaturan global, konfigurasi AI, hasil sinkronisasi, login/logout, penghapusan riwayat chat, dan operasi backup/restore. Perubahan state dan audit dilakukan dalam transaksi SQLite yang sama. Password/token/API key disamarkan berdasarkan nama field; key AI tidak dikirim kembali ke browser.

Tabel audit menyediakan filter pengguna, jenis data, rentang tanggal UTC, 25 baris per halaman, serta detail sebelum/sesudah. Waktu hasil mengikuti zona tampilan global. Perubahan nilai pada tabel audit ditolak oleh trigger SQLite; tidak tersedia tombol edit/hapus. Ini perlindungan tingkat aplikasi, bukan jaminan terhadap administrator komputer yang dapat mengubah berkas secara langsung.

Pengujian: `python -m unittest test_backup_audit test_backup_http -v`. Semua pengujian restore memakai database sementara; database pengguna tidak dipulihkan selama pengembangan.
