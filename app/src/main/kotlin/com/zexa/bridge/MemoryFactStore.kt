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

    fun normalizeImportFacts(values: List<String>): List<String> {
        if (values.size > MAX_FACTS) throw IllegalArgumentException("Backup contains more than $MAX_FACTS facts.")
        return values.map { value ->
            normalize(value) ?: throw IllegalArgumentException("Backup contains a blank or oversized memory fact.")
        }.distinctBy { it.lowercase() }
    }
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

    /** Merge a validated backup atomically. Existing facts are kept; case-insensitive duplicates are skipped. */
    @Synchronized fun mergeImportedFacts(facts: List<String>): Int {
        val normalized = MemoryFactRules.normalizeImportFacts(facts)
        val db = writableDatabase
        db.beginTransaction()
        try {
            val existing = db.rawQuery("SELECT COUNT(*) FROM $TABLE_FACTS", null).use { it.moveToFirst(); it.getInt(0) }
            val additions = normalized.filterNot { fact ->
                db.rawQuery("SELECT 1 FROM $TABLE_FACTS WHERE fact = ? COLLATE NOCASE LIMIT 1", arrayOf(fact)).use { it.moveToFirst() }
            }
            if (existing + additions.size > MemoryFactRules.MAX_FACTS) {
                throw IllegalStateException("Restore would exceed the " + MemoryFactRules.MAX_FACTS + "-fact memory limit. No changes were made.")
            }
            val now = System.currentTimeMillis()
            additions.forEach { fact ->
                val values = ContentValues().apply { put("fact", fact); put("updated_at", now) }
                if (db.insertWithOnConflict(TABLE_FACTS, null, values, SQLiteDatabase.CONFLICT_IGNORE) == -1L) {
                    throw IllegalStateException("Could not restore a memory fact. No changes were made.")
                }
            }
            db.setTransactionSuccessful()
            return additions.size
        } finally {
            db.endTransaction()
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
