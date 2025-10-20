const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

const logger = pino({ level: 'silent' });

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    
    const sock = makeWASocket({
        auth: state,
        logger,
        browser: ['WhatsApp Checker Bot', 'Chrome', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            console.log('\nðŸ” Scan this QR code with WhatsApp to authenticate:\n');
            qrcode.generate(qr, { small: true });
        }
        
        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error instanceof Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('Connection closed. Reconnecting:', shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === 'open') {
            console.log('âœ… WhatsApp bot connected successfully!');
            console.log('ðŸ“± Ready to process commands.');
            console.log('\nUsage: Send a message with .chk <start_number> <end_number>');
            console.log('Example: .chk 947668502000 947668502100\n');
        }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;
        
        const msg = messages[0];
        if (!msg.message) return;
        
        const messageText = msg.message.conversation || 
                           msg.message.extendedTextMessage?.text || '';
        
        const sender = msg.key.remoteJid;
        
        if (messageText.toLowerCase().startsWith('.chk')) {
            await handleCheckCommand(sock, sender, messageText, msg);
        }
    });

    return sock;
}

async function handleCheckCommand(sock, sender, messageText, quotedMsg) {
    const parts = messageText.trim().split(/\s+/);
    
    if (parts.length !== 3) {
        await sock.sendMessage(sender, {
            text: 'âŒ Invalid format!\n\nUsage: .chk <start_number> <end_number>\nExample: .chk 947668502000 947668502100'
        }, { quoted: quotedMsg });
        return;
    }

    const startNumber = parts[1];
    const endNumber = parts[2];

    const numbers = generateNumberRange(startNumber, endNumber);
    
    if (!numbers || numbers.length === 0) {
        await sock.sendMessage(sender, {
            text: 'âŒ Invalid number range. Please check your input.'
        }, { quoted: quotedMsg });
        return;
    }

    if (numbers.length > 20001) {
        await sock.sendMessage(sender, {
            text: `âŒ Range too large (${numbers.length} numbers). Maximum 1000 numbers allowed per check.`
        }, { quoted: quotedMsg });
        return;
    }

    const timestamp = `${startNumber}_${endNumber}`;
    const filename = `${timestamp}.txt`;
    const filepath = path.join(__dirname, filename);

    await sock.sendMessage(sender, {
        text: `ðŸ” Checking ${numbers.length} numbers...\nâ±ï¸ Estimated time: ${Math.ceil(numbers.length / 15 * 30)} seconds (${Math.ceil(numbers.length / 15 * 30 / 60)} minutes)\nðŸ“ Results will be saved progressively to: ${filename}\n\nâš ï¸ Using slow mode with long delays to prevent bans`
    }, { quoted: quotedMsg });

    const results = await checkWhatsAppNumbers(sock, numbers, filepath, startNumber, endNumber, sender, quotedMsg);
    
    const summary = `âœ… Check completed!\n\n` +
                   `ðŸ“Š Total checked: ${numbers.length}\n` +
                   `âœ“ On WhatsApp: ${results.registered.length}\n` +
                   `âœ— Not on WhatsApp: ${results.notRegistered.length}\n\n` +
                   `ðŸ“„ Final results saved to: ${filename}`;

    await sock.sendMessage(sender, { text: summary }, { quoted: quotedMsg });
    
    if (results.registered.length > 0 && results.registered.length <= 100) {
        const listText = 'ðŸ“± WhatsApp Numbers:\n\n' + 
                        results.registered.slice(0, 50).join('\n') +
                        (results.registered.length > 50 ? `\n\n... and ${results.registered.length - 50} more (see file)` : '');
        await sock.sendMessage(sender, { text: listText });
    }
    
    console.log(`âœ… Check completed for ${sender}. Results saved to ${filename}`);
}

function generateNumberRange(startStr, endStr) {
    const start = startStr.replace(/[^0-9]/g, '');
    const end = endStr.replace(/[^0-9]/g, '');
    
    if (start.length !== end.length) {
        return null;
    }
    
    const startNum = BigInt(start);
    const endNum = BigInt(end);
    
    if (startNum > endNum) {
        return null;
    }
    
    const numbers = [];
    const padding = start.length;
    
    for (let i = startNum; i <= endNum; i++) {
        const numStr = i.toString().padStart(padding, '0');
        numbers.push(numStr);
    }
    
    return numbers;
}

async function checkWhatsAppNumbers(sock, numbers, filepath, startNumber, endNumber, sender, quotedMsg) {
    const registered = [];
    const notRegistered = [];
    const minBatchSize = 10;  // Reduced from 20
    const maxBatchSize = 25;  // Reduced from 50
    
    console.log(`Checking ${numbers.length} numbers with randomized batching...`);
    
    let processedCount = 0;
    let batchNumber = 0;
    
    while (processedCount < numbers.length) {
        batchNumber++;
        
        // Randomize batch size between 10-25
        const batchSize = Math.floor(Math.random() * (maxBatchSize - minBatchSize + 1)) + minBatchSize;
        const batch = numbers.slice(processedCount, processedCount + batchSize);
        const jids = batch.map(num => `${num}@s.whatsapp.net`);
        
        let retryCount = 0;
        let success = false;
        
        while (retryCount < 3 && !success) {
            try {
                const results = await sock.onWhatsApp(...jids);
                
                const registeredJids = new Set(
                    results.filter(r => r.exists).map(r => r.jid)
                );
                
                batch.forEach(num => {
                    const jid = `${num}@s.whatsapp.net`;
                    if (registeredJids.has(jid)) {
                        registered.push(num);
                    } else {
                        notRegistered.push(num);
                    }
                });
                
                success = true;
                processedCount += batch.length;
                
                console.log(`âœ“ Batch ${batchNumber}: ${processedCount}/${numbers.length} (${batch.length} numbers)`);
                
                // Save progress after every batch
                const fileContent = generateResultFile({ registered, notRegistered }, startNumber, endNumber, processedCount, numbers.length);
                fs.writeFileSync(filepath, fileContent);
                console.log(`ðŸ’¾ Progress saved: ${processedCount}/${numbers.length}`);
                
                // Send progress update every 100 numbers
                if (processedCount % 100 === 0 && processedCount < numbers.length) {
                    await sock.sendMessage(sender, {
                        text: `ðŸ“Š Progress: ${processedCount}/${numbers.length}\nâœ“ Found: ${registered.length} numbers`
                    }, { quoted: quotedMsg });
                }
                
            } catch (error) {
                retryCount++;
                console.error(`âŒ Error in batch ${batchNumber} (attempt ${retryCount}/3):`, error.message);
                
                if (retryCount >= 3) {
                    batch.forEach(num => notRegistered.push(num));
                    processedCount += batch.length;
                    console.log(`âš ï¸ Batch ${batchNumber} failed after 3 attempts, marked as not registered`);
                } else {
                    // Wait much longer before retry
                    const retryDelay = 15000 * retryCount; // 15-45 seconds
                    console.log(`â³ Retrying in ${retryDelay/1000} seconds...`);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                }
            }
        }
        
        if (processedCount < numbers.length) {
            // Much longer delays to prevent bans
            const baseDelay = 8000; // 8 seconds base (increased from 3)
            const randomDelay = Math.floor(Math.random() * 12000) + 8000; // 8-20 seconds random
            const progressiveDelay = Math.min(batchNumber * 500, 15000); // Progressive up to 15 seconds
            const totalDelay = baseDelay + randomDelay + progressiveDelay;
            
            console.log(`â±ï¸ Waiting ${(totalDelay/1000).toFixed(1)}s before next batch...`);
            await new Promise(resolve => setTimeout(resolve, totalDelay));
            
            // Extra long pause every 10 batches
            if (batchNumber % 10 === 0) {
                const extraPause = 60000; // 1 minute
                console.log(`â¸ï¸ Taking a longer break (${extraPause/1000}s) to avoid detection...`);
                await new Promise(resolve => setTimeout(resolve, extraPause));
            }
        }
    }
    
    return { registered, notRegistered };
}

function generateResultFile(results, startNumber, endNumber, processedCount, totalCount) {
    const timestamp = new Date().toLocaleString();
    const lines = [];
    
    lines.push('='.repeat(60));
    lines.push('WhatsApp Number Checker - Results');
    lines.push('='.repeat(60));
    lines.push(`Range: ${startNumber} - ${endNumber}`);
    lines.push(`Generated: ${timestamp}`);
    
    if (processedCount && totalCount) {
        lines.push(`Progress: ${processedCount}/${totalCount} (${((processedCount/totalCount)*100).toFixed(1)}%)`);
    }
    
    lines.push('='.repeat(60));
    lines.push(`On WhatsApp: ${results.registered.length}`);
    lines.push(`Not on WhatsApp: ${results.notRegistered.length}`);
    lines.push('='.repeat(60));
    lines.push('');
    
    if (results.registered.length > 0) {
       // lines.push('ðŸ“± REGISTERED ON WHATSAPP:');
        ///lines.push('');
        results.registered.forEach(num => lines.push(num));
    } else {
        lines.push('No numbers found on WhatsApp');
    }
    
    lines.push('');
    lines.push('='.repeat(60));
    
    return lines.join('\n');
}

console.log('ðŸ¤– WhatsApp Number Checker Bot');
console.log('================================\n');

connectToWhatsApp().catch(err => {
    console.error('Error starting bot:', err);
});
