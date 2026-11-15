package com.zexa.bridge

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class MemoryFact(val id: Long, val fact: String, val updatedAt: Long)

object MemoryFactRules {
    const val MAX_FACT_LENGTH = 500
    const val MAX_FACTS = 100
    fun normalize(value: String): String? = value.trim().takeIf { it.isNotEmpty() && it.length <= MAX_FACT_LENGTH }
}

/** Explicitly user-managed facts. Nothing is extracted from chat automatically. */
class MemoryFactStore(context: Context) :
    SQLiteOpenHelper(context.applicationContext, DATABASE_NAME, null, DATABASE_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE $TABLE_FACTS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL COLLATE NOCASE UNIQUE,
                updated_at INTEGER NOT NULL
            )
        """.trimIndent())
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    @Synchronized fun all(): List<MemoryFact> = queryFacts(null)

    @Synchronized fun search(query: String): List<MemoryFact> {
        val term = query.trim()
        if (term.isEmpty()) return all()
        val escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return queryFacts("%$escaped%")
    }

    private fun queryFacts(pattern: String?): List<MemoryFact> {
        val result = ArrayList<MemoryFact>()
        val sql = if (pattern == null)
            "SELECT id, fact, updated_at FROM $TABLE_FACTS ORDER BY updated_at DESC, id DESC"
        else
            "SELECT id, fact, updated_at FROM $TABLE_FACTS WHERE fact LIKE ? ESCAPE '\\' ORDER BY updated_at DESC, id DESC"
        readableDatabase.rawQuery(sql, if (pattern == null) null else arrayOf(pattern)).use { cursor ->
            while (cursor.moveToNext()) result.add(MemoryFact(cursor.getLong(0), cursor.getString(1), cursor.getLong(2)))
        }
        return result
    }

    @Synchronized fun save(id: Long?, value: String): Long {
        val fact = MemoryFactRules.normalize(value) ?: throw IllegalArgumentException("Fact must contain 1–500 characters.")
        val db = writableDatabase
        if (id == null) {
            val count = db.rawQuery("SELECT COUNT(*) FROM $TABLE_FACTS", null).use { it.moveToFirst(); it.getInt(0) }
            if (count >= MemoryFactRules.MAX_FACTS) throw IllegalStateException("Memory is full. Delete a fact before adding another.")
        }
        val values = ContentValues().apply {
            put("fact", fact)
            put("updated_at", System.currentTimeMillis())
        }
        return if (id == null) db.insertOrThrow(TABLE_FACTS, null, values) else {
            val changed = db.update(TABLE_FACTS, values, "id = ?", arrayOf(id.toString()))
            if (changed == 0) throw IllegalArgumentException("This memory fact no longer exists.")
            id
        }
    }

    @Synchronized fun delete(id: Long): Boolean =
        writableDatabase.delete(TABLE_FACTS, "id = ?", arrayOf(id.toString())) > 0

    @Synchronized fun clear() { writableDatabase.delete(TABLE_FACTS, null, null) }

    companion object {
        private const val DATABASE_NAME = "zexa_personal_memory.db"
        private const val DATABASE_VERSION = 1
        private const val TABLE_FACTS = "memory_facts"
    }
}
