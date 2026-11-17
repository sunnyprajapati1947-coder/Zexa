package com.zexa.bridge

import org.json.JSONObject

/** Narrow service contract so the loopback HTTP server can be tested without Android runtime. */
internal interface BridgeServiceApi {
    fun statusJson(): JSONObject
    fun activeTaskActionGrants(): List<TaskActionGrant>
    fun revokeTaskActionGrant(grantId: String): Boolean
    fun screenJson(): JSONObject
    fun performGrantedAction(taskId: String, grantId: String, action: String, payload: JSONObject): JSONObject
    fun queueActionForApproval(action: String, payload: JSONObject): JSONObject
    fun actionResult(requestId: String): JSONObject?
}
