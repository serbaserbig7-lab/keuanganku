import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import uuid

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Buku Kas Pribadi", layout="wide")
st.title("💸 Catatan Pendapatan & Pengeluaran")

# --- VALIDASI KREDENSIAL JSONBIN ---

# --- SUNTIKAN CSS TEMA IQAIR ---
st.markdown("""
<style>
    /* 1. Mengimpor Font 'Inter' dari Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* 2. Menerapkan Font ke Seluruh Aplikasi */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 3. Mengubah Warna Latar Belakang (Soft Gray ala IQAir) */
    .stApp {
        background-color: #F4F7F6;
    }

    /* 4. Menata Gaya Kartu Metrik (Saldo, Pemasukan, Pengeluaran) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        border: 1px solid #E5E7EB;
        transition: transform 0.2s ease-in-out;
    }
    
    /* Efek melayang saat kursor diarahkan ke kartu metrik */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
    }

    /* 5. Mempercantik Tombol (Warna Biru Modern) */
    .stButton > button {
        background-color: #0B5ED7;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #094eb3;
        box-shadow: 0 4px 8px rgba(11, 94, 215, 0.3);
        color: white;
    }
    
    /* Tombol Hapus (Warna Merah) */
    button[kind="primary"] {
        background-color: #DC3545;
    }
    button[kind="primary"]:hover {
        background-color: #bb2d3b;
        box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
    }

    /* 6. Mempercantik Formulir Input */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)


try:
    BIN_ID = st.secrets["jsonbin"]["bin_id"]
    API_KEY = st.secrets["jsonbin"]["api_key"]
    URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"

    HEADERS = {
        "X-Master-Key": API_KEY,
        "Content-Type": "application/json"
    }
except KeyError as e:
    st.error(f"Kunci Rahasia (Secret Key) tidak ditemukan: {e}")
    st.warning("Pastikan format di Streamlit Cloud Secrets sama persis (perhatikan huruf besar/kecil).")
    st.stop()
except Exception as e:
    st.error(f"Terjadi kesalahan sistem: {e}")
    st.stop()

# --- FUNGSI BACA & TULIS KE AWAN ---
@st.cache_data(ttl=0)
def load_data():
    try:
        response = requests.get(URL, headers=HEADERS)
        if response.status_code == 200:
            return response.json().get("record", [])
        return []
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        return []

def save_data(data):
    try:
        response = requests.put(URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Detail Error API: Kode {response.status_code} | {response.text}")
            return False
    except Exception as e:
        st.error(f"Gagal koneksi internet: {e}")
        return False

# Memuat data
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# Fungsi untuk menghapus item
def delete_transaction(item_id):
    st.session_state.data = [item for item in st.session_state.data if item.get('id') != item_id]
    if save_data(st.session_state.data):
        st.toast("Transaksi berhasil dihapus!", icon="🗑️")
    else:
        st.error("Gagal menghapus di cloud.")

# --- TATA LETAK: DUA KOLOM UTAMA ---
col1, col2 = st.columns([1, 2.5])

# KOLOM 1: FORMULIR INPUT
with col1:
    st.subheader("Tambah Transaksi")
    with st.form(key="form_transaksi", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", datetime.today())
        tipe = st.radio("Tipe Transaksi", ["Pemasukan", "Pengeluaran"], horizontal=True)
        kategori = st.selectbox("Kategori", ["Gaji", "Belanja Istri", "Makanan", "Transportasi", "Utilitas", "Hiburan", "Investasi", "Lainnya"])
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000)
        keterangan = st.text_input("Keterangan")
        
        submit_button = st.form_submit_button(label="Simpan Transaksi")
        
        if submit_button:
            if nominal > 0:
                transaksi_baru = {
                    "id": str(uuid.uuid4()), # Memberikan ID unik untuk keperluan edit/hapus
                    "tanggal": str(tanggal),
                    "tipe": tipe,
                    "kategori": kategori,
                    "nominal": nominal,
                    "keterangan": keterangan
                }
                st.session_state.data.append(transaksi_baru)
                
                if save_data(st.session_state.data):
                    st.success("Tersimpan!")
                    st.rerun()
                else:
                    st.session_state.data.pop() # Rollback jika gagal simpan
            else:
                st.error("Nominal harus lebih dari 0!")

# KOLOM 2: RINGKASAN, GRAFIK & MANAJEMEN TABEL
with col2:
    st.subheader("Ringkasan Keuangan")
    
    if len(st.session_state.data) > 0:
        df = pd.DataFrame(st.session_state.data)
        
        # Pengamanan tipe data
        df['nominal'] = pd.to_numeric(df['nominal'], errors='coerce').fillna(0)
        
        # UBAH TEKS MENJADI FORMAT TANGGAL
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce').dt.date
        
        # Hitung Total
        total_masuk = df[df['tipe'] == 'Pemasukan']['nominal'].sum()
        total_keluar = df[df['tipe'] == 'Pengeluaran']['nominal'].sum()
        saldo = total_masuk - total_keluar
        
        # Tampilkan Kartu Metrik
        metrik_1, metrik_2, metrik_3 = st.columns(3)
        metrik_1.metric("Pemasukan", f"Rp {total_masuk:,.0f}")
        metrik_2.metric("Pengeluaran", f"Rp {total_keluar:,.0f}")
        metrik_3.metric("Sisa Saldo", f"Rp {saldo:,.0f}")
        
        st.divider()
        
        # --- BAGIAN GRAFIK VISUALISASI ---
        st.markdown("##### 📊 Analisis Pengeluaran per Kategori")
        df_pengeluaran = df[df['tipe'] == 'Pengeluaran']
        
        if not df_pengeluaran.empty:
            # Mengelompokkan data berdasarkan kategori
            df_grouped = df_pengeluaran.groupby('kategori', as_index=False)['nominal'].sum()
            
            fig = px.pie(
                df_grouped, 
                values='nominal', 
                names='kategori', 
                hole=0.4, # Membuat donut chart
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data pengeluaran untuk ditampilkan pada grafik.")
            
        st.divider()
        
        # --- BAGIAN MANAJEMEN TABEL (EDIT/HAPUS) ---
        st.markdown("##### 📝 Manajemen Riwayat Transaksi")
        
        # Tampilkan tabel yang lebih rapi
        df_tampil = df.sort_values(by="tanggal", ascending=False).reset_index(drop=True)
        
        # Gunakan st.data_editor agar bisa langsung diedit di tabel
        edited_df = st.data_editor(
            df_tampil,
            hide_index=True,
            column_order=["tanggal", "tipe", "kategori", "nominal", "keterangan"],
            column_config={
                "tanggal": st.column_config.DateColumn("Tanggal"),
                "tipe": st.column_config.SelectboxColumn("Tipe", options=["Pemasukan", "Pengeluaran"]),
                "kategori": st.column_config.SelectboxColumn("Kategori", options=["Gaji", "Makanan", "Transportasi", "Utilitas", "Hiburan", "Investasi", "Lainnya"]),
                "nominal": st.column_config.NumberColumn("Nominal", format="Rp %d"),
                "id": None # Sembunyikan kolom ID
            },
            num_rows="dynamic", # Memungkinkan penambahan baris langsung dari tabel
            key="data_editor",
            use_container_width=True
        )

        # Logika untuk menyimpan perubahan (Edit)
        if st.button("💾 Simpan Perubahan Tabel"):
            # Konversi kembali DF yang diedit ke bentuk dictionary/JSON
            # Pastikan format tanggal kembali ke string
            edited_df['tanggal'] = edited_df['tanggal'].astype(str)
            updated_data = edited_df.to_dict('records')
            
            # Pastikan ID tetap ada atau ter-generate jika baris baru ditambah manual
            for item in updated_data:
                if 'id' not in item or pd.isna(item['id']):
                     item['id'] = str(uuid.uuid4())
            
            st.session_state.data = updated_data
            if save_data(updated_data):
                st.success("Perubahan tabel berhasil disimpan ke cloud!")
                st.rerun()
                
        # Logika Khusus Hapus Data
        st.markdown("Atau hapus spesifik transaksi:")
        hapus_col1, hapus_col2 = st.columns([3, 1])
        with hapus_col1:
            opsi_hapus = {f"{row['tanggal']} | {row['tipe']} - Rp {row['nominal']:,.0f} ({row['keterangan']})": row['id'] 
                          for index, row in df_tampil.iterrows() if pd.notna(row.get('id'))}
            pilihan_hapus = st.selectbox("Pilih transaksi yang ingin dihapus:", options=list(opsi_hapus.keys()))
        with hapus_col2:
            st.write("")
            st.write("") # Spacer agar tombol sejajar
            if st.button("🗑️ Hapus", type="primary", use_container_width=True):
                if pilihan_hapus:
                    id_target = opsi_hapus[pilihan_hapus]
                    delete_transaction(id_target)
                    st.rerun()

    else:
        st.info("Belum ada data transaksi. Silakan input transaksi pertama Anda!")
