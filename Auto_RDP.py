import subprocess
import time

# ==========================================
# KONFIGURASI VPN & RDP
# ==========================================
VPN_NAME = "Surge"
RDP_IP = "10.48.38.9"
RDP_USER = r"orexsaiidn\orexsai006"
RDP_PASS = "Orex_sai8417#"

def buka_koneksi_rdp():
    try:
        print(f"\n[RDP OTOMATIS] 1. Mencoba menghubungkan VPN '{VPN_NAME}'...")
        hasil_vpn = subprocess.run(["rasdial", VPN_NAME, r"dvfernando@orex", "#fernando53"], capture_output=True, text=True)
        if hasil_vpn.returncode != 0:
            print(f"⚠️ [WARNING] Gagal menghubungkan VPN! Pesan dari sistem:")
            print(f"{hasil_vpn.stdout}\n{hasil_vpn.stderr}")
        else:
            print("✅ VPN Surge berhasil terhubung otomatis!")

        print("[RDP OTOMATIS] Menunggu 5 detik agar jalur jaringan VPN stabil...")
        time.sleep(5)  
        
        print(f"[RDP OTOMATIS] 2. Menyuntikkan kredensial RDP untuk user '{RDP_USER}'...")
        subprocess.run(["cmdkey", f"/generic:TERMSRV/{RDP_IP}", f"/user:{RDP_USER}", f"/pass:{RDP_PASS}"], capture_output=True)
        
        print(f"[RDP OTOMATIS] 3. Meluncurkan Remote Desktop ke {RDP_IP}...")
        subprocess.Popen(["mstsc", f"/v:{RDP_IP}"])

        print("[RDP OTOMATIS] 4. Memproses Auto-Login ke vRAN-EMS...")

        # ==========================================
        # 4. OTOMATISASI KETIK DALAM RDP (POWERSHELL)
        # ==========================================
        powershell_script = """
        Start-Sleep -Seconds 8

        # Paksa Jendela RDP Fokus
        $cs = 'using System; using System.Runtime.InteropServices; public class Win32 { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); }'
        Add-Type -TypeDefinition $cs
        $mstsc = Get-Process mstsc -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($mstsc) { [Win32]::SetForegroundWindow($mstsc.MainWindowHandle) }
        
        Start-Sleep -Seconds 2
        $wshell = New-Object -ComObject wscript.shell

        # 1. Buka Start Menu & Ketik Firefox
        $wshell.SendKeys("^{ESC}")
        Start-Sleep -Seconds 2
        
        $app = "firefox"
        foreach ($c in $app.ToCharArray()) { $wshell.SendKeys($c.ToString()); Start-Sleep -Milliseconds 20 }
        Start-Sleep -Milliseconds 100
        $wshell.SendKeys("{ENTER}")
        
        # 2. Tunggu Firefox Terbuka
        Start-Sleep -Seconds 12
        $wshell.SendKeys("^l")
        Start-Sleep -Seconds 1

        # 3. Ketik URL Pendek (Otomatis Redirect Nanti)
        $url = "https://internal-emsmain.ems-orex.jia.co.id/SDVF/visualframe/FB010-0025"
        foreach ($c in $url.ToCharArray()) { $wshell.SendKeys($c.ToString()); Start-Sleep -Milliseconds 20 }
        Start-Sleep -Milliseconds 100
        $wshell.SendKeys("{ENTER}")

        # 4. Tunggu 15 DETIK untuk proses Redirect Keycloak
        Start-Sleep -Seconds 15

        # Paksa Jendela RDP Fokus Lagi (Jaga-jaga jika terlepas)
        $mstsc2 = Get-Process mstsc -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($mstsc2) { [Win32]::SetForegroundWindow($mstsc2.MainWindowHandle) }
        Start-Sleep -Seconds 1

        # 5. Ketik Username ke form login yang sudah siap
        $user = "5g_ems_user_su"
        foreach ($c in $user.ToCharArray()) { $wshell.SendKeys($c.ToString()); Start-Sleep -Milliseconds 40 }
        Start-Sleep -Milliseconds 50
        
        # Pindah ke kolom Password
        $wshell.SendKeys("{TAB}")
        Start-Sleep -Seconds 1

        # 6. Ketik Password & Sign In
        $pass = "Su_2026#"
        foreach ($c in $pass.ToCharArray()) { $wshell.SendKeys($c.ToString()); Start-Sleep -Milliseconds 40 }
        Start-Sleep -Milliseconds 50
        $wshell.SendKeys("{ENTER}")
        """
        
        subprocess.Popen(["powershell", "-Command", powershell_script])

        return f"✅ VPN terhubung, RDP {RDP_IP} diluncurkan, & Auto-Login vRAN-EMS diproses!"
    except Exception as e:
        error_msg = f"❌ Gagal memproses VPN/RDP. Error: {e}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    buka_koneksi_rdp()