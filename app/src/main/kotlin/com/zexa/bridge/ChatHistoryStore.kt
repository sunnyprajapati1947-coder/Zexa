package com.zexa.bridge

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Stores the most recent completed local chat turns in the app-private database.
 * No network or external storage access is used.
 */
class ChatHistoryStore(context: Context) :
    SQLiteOpenHelper(context.applicationContext, DATABASE_NAME, null, DATABASE_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE $TABLE_MESSAGES (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """.trimIndent()
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // No destructive migration is needed for the current single-version schema.
    }

    @Synchronized
    fun loadRecent(limit: Int = DEFAULT_HISTORY_LIMIT): List<Pair<String, String>> {
        val safeLimit = limit.coerceIn(1, MAX_HISTORY_LIMIT)
        val result = ArrayList<Pair<String, String>>()
        readableDatabase.rawQuery(
            "SELECT role, content FROM $TABLE_MESSAGES ORDER BY id DESC LIMIT ?",
            arrayOf(safeLimit.toString())
        ).use { cursor ->
            while (cursor.moveToNext()) {
                result.add(cursor.getString(0) to cursor.getString(1))
            }
        }
        result.reverse()
        return result
    }

    /**
     * Replaces the stored conversation atomically. Call after a completed assistant response,
     * so interrupted generations do not leave an unanswered user message in durable history.
     */
    @Synchronized
    fun saveCompletedConversation(messages: List<Pair<String, String>>) {
        val bounded = messages.takeLast(MAX_HISTORY_LIMIT)
        require(bounded.all { (role, content) ->
            (role == "user" || role == "assistant") && content.isNotBlank()
        }) { "Conversation contains an invalid role or empty message." }

        val db = writableDatabase
        db.beginTransaction()
        try {
            db.delete(TABLE_MESSAGES, null, null)
            val now = System.currentTimeMillis()
            bounded.forEachIndexed { index, (role, content) ->
                val values = ContentValues().apply {
                    put("role", role)
                    put("content", content)
                    put("created_at", now + index)
                }
                db.insertOrThrow(TABLE_MESSAGES, null, values)
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    @Synchronized
    fun clear() {
        writableDatabase.delete(TABLE_MESSAGES, null, null)
    }

    companion object {
        const val DEFAULT_HISTORY_LIMIT = 15
        const val MAX_HISTORY_LIMIT = 200
        private const val DATABASE_NAME = "zexa_chat_history.db"
        private const val DATABASE_VERSION = 1
        private const val TABLE_MESSAGES = "messages"
    }
}
