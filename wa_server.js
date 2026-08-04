const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth() // Menyimpan sesi login agar tidak scan QR terus-menerus
});

let isReady = false;

client.on('qr', (qr) => {
    console.log('\n=== PLEASE SCAN THIS QR CODE WITH YOUR WHATSAPP ===');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    isReady = true;
    console.log('🤖 Local WhatsApp Bot (Bridge) Ready to Go Live!');
});

client.initialize();

// Endpoint lokal yang akan dipanggil oleh skrip Python Anda
app.post('/send', async (req, res) => {
    if (!isReady) {
        return res.status(500).json({ status: false, message: 'The WhatsApp app is not ready yet' });
    }

    const { target, message, imagePath } = req.body;

    try {
        // Cek apakah ada file gambar yang ingin dikirim
        if (imagePath && fs.existsSync(imagePath)) {
            const absolutePath = path.resolve(imagePath);
            const media = MessageMedia.fromFilePath(absolutePath);
            await client.sendMessage(target, media, { caption: message || '' });
            console.log(`✅ Successfully sent a photo to WA: ${target}`);
        } else {
            // Jika hanya pesan teks biasa
            await client.sendMessage(target, message);
            console.log(`✅ Successfully sent a photo to WA: ${target}`);
        }
        res.json({ status: true, message: 'Successfully sent to WhatsApp' });
    } catch (error) {
        console.error('❌ Failed send to WhatsApp:', error);
        res.status(500).json({ status: false, error: error.message });
    }
});

app.listen(3000, () => {
    console.log('🚀 WA Local Bridge runs on http://localhost:3000');
});