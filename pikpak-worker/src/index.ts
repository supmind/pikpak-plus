import { PikPakApi } from './pikpak_api';

export interface Env {
    TELEGRAM_BOT_TOKEN: string;
    PIKPAK_USERNAME?: string;
    PIKPAK_PASSWORD?: string;
    DB: KVNamespace;
}

// Telegram Types
interface Update {
    update_id: number;
    message?: Message;
    pre_checkout_query?: PreCheckoutQuery;
}

interface Message {
    message_id: number;
    chat: { id: number };
    text?: string;
    successful_payment?: SuccessfulPayment;
}

interface PreCheckoutQuery {
    id: string;
    from: { id: number; first_name: string };
    currency: string;
    total_amount: number;
    invoice_payload: string;
}

interface SuccessfulPayment {
    currency: string;
    total_amount: number;
    invoice_payload: string;
    telegram_payment_charge_id: string;
    provider_payment_charge_id: string;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        if (request.method === "POST") {
            try {
                const update: Update = await request.json();
                await handleUpdate(update, env);
            } catch (e) {
                console.error("Error handling update", e);
            }
            return new Response("OK");
        }
        return new Response("PikPak Bot Worker is Running");
    },
};

async function handleUpdate(update: Update, env: Env) {
    // 1. Handle Messages
    if (update.message) {
        const chatId = update.message.chat.id;

        // A. Successful Payment
        if (update.message.successful_payment) {
            await handleSuccessfulPayment(chatId, update.message.successful_payment, env);
            return;
        }

        // B. Text Commands / Links
        const text = update.message.text;
        if (!text) return;

        if (text.startsWith("/start")) {
            await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, "欢迎使用 PikPak 离线下载助手！\n请发送磁力链接 (magnet:?xt=...) 或下载链接，我将为您下载。\n收费标准：10GB 以下文件收取 1 Star。");
        } else if (text.startsWith("magnet:") || text.startsWith("http")) {
            // Initiate Invoice
            await sendInvoice(env.TELEGRAM_BOT_TOKEN, chatId, text);
        } else {
            await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, "请发送有效的磁力链接或 HTTP 链接。");
        }
    }

    // 2. Handle Pre-Checkout Query (Must answer within 10s)
    if (update.pre_checkout_query) {
        await answerPreCheckoutQuery(env.TELEGRAM_BOT_TOKEN, update.pre_checkout_query.id, true);
    }
}

// --- Telegram Methods ---

async function sendMessage(token: string, chatId: number, text: string) {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text }),
    });
}

async function sendInvoice(token: string, chatId: number, fileUrl: string) {
    const url = `https://api.telegram.org/bot${token}/sendInvoice`;
    const payload = {
        chat_id: chatId,
        title: "PikPak 离线下载服务",
        description: "高速离线下载至云端 (限10GB以内)",
        payload: JSON.stringify({ url: fileUrl, ts: Date.now() }), // Store URL in payload
        provider_token: "", // Empty for Telegram Stars
        currency: "XTR", // Currency for Stars
        prices: [{ label: "本次下载费用", amount: 1 }], // 1 Star
        start_parameter: "pay",
    };

    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    // console.log("SendInvoice", await res.text());
}

async function answerPreCheckoutQuery(token: string, queryId: string, ok: boolean, errorMessage?: string) {
    const url = `https://api.telegram.org/bot${token}/answerPreCheckoutQuery`;
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pre_checkout_query_id: queryId, ok, error_message: errorMessage }),
    });
}

// --- Business Logic ---

async function handleSuccessfulPayment(chatId: number, payment: SuccessfulPayment, env: Env) {
    // 1. Parse Payload
    let payload;
    try {
        payload = JSON.parse(payment.invoice_payload);
    } catch (e) {
        await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, "支付数据解析失败，请联系管理员。");
        return;
    }

    const fileUrl = payload.url;

    // 2. Notify User
    await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, "支付成功！正在为您提交离线下载任务...");

    // 3. Call PikPak API
    try {
        const pikpak = new PikPakApi({
            username: env.PIKPAK_USERNAME,
            password: env.PIKPAK_PASSWORD,
        });

        await pikpak.login();
        const taskRes = await pikpak.offlineDownload(fileUrl);

        // taskRes usually contains "task" or "upload_type" info.
        // If it's a magnet, it creates a task.

        const taskId = taskRes.task?.id || taskRes.file?.id; // Adjust based on actual response structure

        if (taskId) {
            // Record in KV (optional)
            await env.DB.put(`task:${taskId}`, JSON.stringify({ chatId, fileUrl, status: "submitted" }));

            await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, `任务已提交 (ID: ${taskId})。\n请稍候，下载完成后将发送链接给您。`);

            // Note: In a real worker, we can't "wait" indefinitely.
            // Ideally, we should check status immediately, or use a Scheduled Handler (Cron Trigger) to poll tasks.
            // For this simple demo, we'll try to check status after a short delay or just give the user the file ID if it was instant.

            // If it was an instant save (like existing file on server), we might have a file_id immediately.
            if (taskRes.file && taskRes.file.id && taskRes.file.phase === "PHASE_TYPE_COMPLETE") {
                 const downloadLink = await pikpak.getDownloadUrl(taskRes.file.id);
                 await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, `下载完成！\n链接: ${downloadLink}`);
            } else {
                 // For long running tasks, we ideally need a Cron Trigger.
                 // Since this is a simple "Pay Per Download" worker, we might not have Cron set up.
                 // We can tell the user to check back later or try to poll a few times here (limited by worker execution time).
                 await checkTaskStatus(pikpak, taskId, env.TELEGRAM_BOT_TOKEN, chatId);
            }

        } else {
            await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, "任务提交响应异常，请联系管理员。");
        }

    } catch (e: any) {
        await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, `任务提交失败: ${e.message}`);
    }
}

async function checkTaskStatus(pikpak: PikPakApi, taskId: string, botToken: string, chatId: number) {
    // Simple polling attempt (e.g., 3 times, 2 seconds apart)
    for (let i = 0; i < 3; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
            // offlineList returns list of tasks. We need to find ours.
            // Or use pikpak.getFile(taskId) if taskId became a fileId (PikPak is complex here, offline tasks vs file IDs)
            // Usually offline_download returns a Task. We list tasks to check phase.
            const listRes = await pikpak.offlineList(20);
            const task = listRes.tasks?.find((t: any) => t.id === taskId);

            if (task) {
                if (task.phase === "PHASE_TYPE_COMPLETE") {
                     const fileId = task.file_id || task.id; // Sometimes task id maps to file, or file_id field exists
                     const downloadLink = await pikpak.getDownloadUrl(fileId);
                     await sendMessage(botToken, chatId, `下载完成！\n链接: ${downloadLink}`);
                     return;
                } else if (task.phase === "PHASE_TYPE_ERROR") {
                     await sendMessage(botToken, chatId, `下载出错: ${task.message || "未知错误"}`);
                     return;
                }
            }
        } catch (e) {
            console.error("Polling error", e);
        }
    }
    await sendMessage(botToken, chatId, "任务正在后台运行。由于 Cloudflare 限制，我无法持续等待。\n(注：此演示版本暂不支持主动推送完成通知，建议改进为 Cron 触发模式)");
}
