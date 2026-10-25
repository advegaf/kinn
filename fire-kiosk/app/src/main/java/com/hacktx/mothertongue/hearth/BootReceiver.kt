package com.hacktx.mothertongue.hearth

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

// Fallback only. Being the HOME app is what really brings Hearth up after boot;
// Android 10+ may block this background activity start otherwise.
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val launch = Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            context.startActivity(launch)
        } catch (_: Exception) {
        }
    }
}
