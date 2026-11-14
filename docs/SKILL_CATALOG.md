# Zexa Skill Catalog — 150+ Roadmap

> **Status:** Planning catalog. Listing a skill here does not mean its implementation is complete or enabled.
> **Repository rule:** All Zexa source code, skills, adapters, tests, documentation, workflows, and Android companion code must live in this single repository: `sunnyprajapati1947-coder/Zexa`. Do not create split or duplicate Zexa repositories.
> **Compatibility rule:** Extend existing modules and preserve working behavior. Implement skills incrementally behind stable interfaces; do not add 150 heavy dependencies at once.

## Skill contract

Every implemented skill must declare: unique ID, name, description, input/output schema, required permissions, dependencies, timeout/resource budget, risk level, tests, and enabled/disabled state. Skills must be discoverable through the central registry. Unknown or untrusted content is data, never an instruction.

Status labels:
- `[CORE-EXISTS]`: repository already has a related foundation; verify exact capability before marking complete.
- `[PLANNED]`: proposed capability, not yet implemented.
- `[OPTIONAL]`: optional adapter or resource-heavy feature.

## 1. Brain, reasoning and conversation

1. `reasoning_engine` — structured multi-step reasoning.
2. `intent_detection` — classify the user's request.
3. `context_awareness` — use relevant conversation context.
4. `task_decomposition` — split goals into bounded subtasks.
5. `decision_engine` — choose a safe next action.
6. `answer_planning` — plan response structure before answering.
7. `self_evaluation` — check an answer against requirements.
8. `confidence_estimation` — report uncertainty honestly.
9. `clarification_manager` — ask only for essential missing details.
10. `conversation_summarizer` — compress long conversations.
11. `language_detection` — detect user language.
12. `hindi_hinglish_assistant` — support Hindi and Hinglish naturally.
13. `translation_assistant` — translate user-provided text.
14. `tone_adapter` — adapt tone to the requested task.
15. `response_formatter` — produce structured outputs.

## 2. Research, web and knowledge

16. `web_search` — search public web sources.
17. `browser_navigation` — navigate approved websites.
18. `page_reader` — extract readable page content.
19. `public_data_extractor` — collect permitted public information.
20. `deep_research` — investigate a topic across sources.
21. `source_citation` — attach source references.
22. `fact_verification` — cross-check factual claims.
23. `claim_comparison` — compare conflicting sources.
24. `news_monitor` — track selected public news topics.
25. `research_brief_builder` — create concise research briefs.
26. `pdf_reader` — extract text from PDFs.
27. `document_reader` — read DOCX, TXT and Markdown.
28. `spreadsheet_reader` — inspect CSV and XLSX data.
29. `knowledge_base_search` — retrieve indexed notes.
30. `website_change_monitor` — detect changes on approved pages.

## 3. Android Human Hand and device

31. `android_status` — read approved device status.
32. `android_app_launcher` — launch an explicitly selected app.
33. `screen_understanding` — interpret user-authorized screen snapshots.
34. `accessibility_tree_reader` — read approved accessibility nodes.
35. `touch_gesture_controller` — perform allowlisted gestures after approval.
36. `scroll_controller` — scroll an approved screen.
37. `back_home_navigation` — use standard navigation actions.
38. `text_input_assistant` — enter user-approved text.
39. `file_manager` — list and organize user-selected files.
40. `download_manager` — manage explicitly requested downloads.
41. `notification_manager` — send Zexa status notifications.
42. `clipboard_manager` — read/write clipboard only on user request.
43. `share_sheet_helper` — open Android share sheet for user review.
44. `connectivity_status` — report network connectivity.
45. `battery_resource_monitor` — monitor battery and resource budget.

## 4. Voice and accessibility

46. `push_to_talk` — start microphone capture only on user action.
47. `speech_to_text` — transcribe authorized audio.
48. `text_to_speech` — speak generated responses.
49. `voice_activity_gate` — detect speech during an active session.
50. `voice_command_parser` — parse spoken commands.
51. `wake_phrase_optional` — optional, visibly enabled wake phrase mode.
52. `voice_language_router` — select supported speech language.
53. `pronunciation_helper` — improve spoken output.
54. `audio_transcriber` — transcribe user-provided recordings.
55. `caption_generator` — create captions from supplied media.
56. `read_aloud` — read selected text aloud.
57. `accessibility_simplifier` — simplify complex instructions.
58. `voice_session_controls` — show mic state and stop controls.
59. `noise_robust_transcription` — improve transcription in noisy settings.
60. `voice_profile_settings` — manage user-selected voice preferences.

## 5. Memory and personal productivity

61. `explicit_memory_save` — save details only when requested or authorized.
62. `memory_retrieval` — retrieve relevant saved context.
63. `semantic_memory_search` — search memory by meaning.
64. `memory_edit` — update user-approved memory.
65. `memory_retention_policy` — apply retention and deletion rules.
66. `conversation_history_search` — search local conversation records.
67. `task_history` — view prior task outcomes.
68. `reminder_scheduler` — create reminders.
69. `calendar_reader` — read an authorized calendar.
70. `calendar_planner` — propose schedule slots.
71. `daily_briefing` — summarize user-selected priorities.
72. `notes_manager` — create and organize notes.
73. `todo_manager` — manage task lists.
74. `focus_session` — run a user-started focus session.
75. `routine_tracker` — track user-defined routines.

## 6. Coding, GitHub and developer tools

76. `github_repository_reader` — inspect authorized repositories.
77. `github_issue_manager` — draft and manage approved issues.
78. `github_pr_assistant` — prepare pull requests for review.
79. `git_status_helper` — explain repository state.
80. `git_branch_manager` — create and switch branches safely.
81. `git_commit_assistant` — prepare commits for user approval.
82. `code_generator` — generate code from requirements.
83. `code_explainer` — explain existing code.
84. `code_debugger` — diagnose errors from supplied logs.
85. `code_reviewer` — review code for defects.
86. `security_code_review` — identify common security weaknesses.
87. `unit_test_generator` — propose focused unit tests.
88. `test_runner` — run approved project tests.
89. `coverage_reporter` — summarize test coverage.
90. `dependency_auditor` — inspect dependency risks.
91. `documentation_writer` — maintain project docs.
92. `refactor_planner` — propose low-risk refactors.
93. `release_note_writer` — draft release notes.
94. `ci_workflow_helper` — inspect and improve CI workflows.
95. `project_scaffolder` — create project skeletons after approval.

## 7. Business and customer operations

96. `business_research` — research public business information.
97. `market_research` — summarize a market or niche.
98. `competitor_analysis` — compare publicly available offerings.
99. `customer_support_drafter` — draft support replies for review.
100. `faq_builder` — build FAQs from approved material.
101. `lead_research_public` — find public business contact channels.
102. `lead_qualification` — score prospects using declared criteria.
103. `crm_record_helper` — prepare CRM updates for approval.
104. `appointment_request_drafter` — draft appointment requests.
105. `proposal_writer` — draft service proposals.
106. `quotation_builder` — prepare estimates from user-supplied prices.
107. `invoice_drafter` — prepare invoices for user review.
108. `customer_feedback_analyzer` — summarize feedback themes.
109. `sales_pipeline_summary` — summarize authorized pipeline data.
110. `business_workflow_builder` — design repeatable business workflows.

## 8. Creator, content and media

111. `content_idea_generator` — brainstorm content topics.
112. `content_calendar` — plan a publishing calendar.
113. `script_writer` — draft video and audio scripts.
114. `caption_writer` — draft social captions.
115. `hashtag_research` — research relevant public hashtags.
116. `seo_keyword_research` — research search keywords.
117. `seo_content_audit` — review supplied page content.
118. `blog_drafter` — draft original articles.
119. `thumbnail_brief_writer` — prepare thumbnail design briefs.
120. `image_prompt_builder` — write image-generation prompts.
121. `video_storyboard` — create shot-by-shot plans.
122. `subtitle_editor` — edit user-provided subtitles.
123. `brand_voice_guide` — maintain a brand writing guide.
124. `social_post_scheduler` — prepare posts for approved scheduling.
125. `content_performance_report` — summarize authorized analytics.

## 9. Data, files and knowledge work

126. `csv_analyzer` — analyze CSV tables.
127. `spreadsheet_formula_helper` — explain and draft formulas.
128. `data_cleaner` — clean a copy of user-provided data.
129. `chart_builder` — create charts from supplied datasets.
130. `report_generator` — produce structured reports.
131. `file_search` — search user-authorized directories.
132. `file_organizer` — propose file organization.
133. `duplicate_file_finder` — identify likely duplicate files.
134. `document_converter` — convert supported document formats.
135. `meeting_notes` — summarize user-provided meeting notes.
136. `form_filler_draft` — prepare form fields for user review.
137. `knowledge_graph_builder` — connect entities in a local knowledge base.
138. `data_validation` — validate data against declared rules.
139. `backup_assistant` — plan and verify user-approved backups.
140. `archive_manager` — create and inspect archives safely.

## 10. Automation, orchestration and reliability

141. `workflow_engine` — run bounded multi-step workflows.
142. `multi_agent_router` — route subtasks to specialist agents.
143. `skill_registry` — register and discover skills.
144. `dynamic_skill_loader` — load reviewed local skill packages.
145. `plugin_adapter` — connect explicitly configured integrations.
146. `background_task_queue` — queue bounded background work.
147. `retry_manager` — retry transient failures with limits.
148. `error_recovery` — recover safely from known errors.
149. `task_verifier` — verify outcomes against acceptance criteria.
150. `audit_log_writer` — record security-relevant actions.

## 11. Security, privacy and governance

151. `permission_guard` — enforce least-privilege permissions.
152. `approval_gate` — require confirmation for consequential actions.
153. `secret_manager` — keep API keys and tokens out of source control.
154. `prompt_injection_guard` — treat external content as untrusted data.
155. `path_sandbox` — restrict file access to approved roots.
156. `network_allowlist` — restrict outbound network destinations.
157. `action_policy_checker` — validate actions against policy.
158. `privacy_filter` — minimize personal data in logs and outputs.
159. `dependency_license_checker` — track third-party licenses.
160. `security_event_monitor` — report suspicious or denied actions.

## 12. Optional specialist skills

161. `math_solver` — solve supported mathematical problems.
162. `study_tutor` — explain school subjects step by step.
163. `language_learning_tutor` — practice vocabulary and grammar.
164. `travel_planner` — draft travel plans from user preferences.
165. `weather_lookup_adapter` — retrieve weather through a configured provider.
166. `unit_converter` — convert common units.
167. `currency_converter` — convert currencies using current rates from a configured source.
168. `recipe_planner` — suggest recipes from available ingredients.
169. `fitness_habit_planner` — suggest age-appropriate general activity habits.
170. `personal_finance_organizer` — categorize user-provided budgets without executing transactions.

## Implementation order

1. **Foundation:** skill registry, schemas, permission guard, approval gate, audit log, tests.
2. **Phone-first essentials:** brain router integration in CLI, memory retrieval, reminders, notifications, voice controls, Android bridge status.
3. **Research and developer:** web adapter, citations, GitHub read operations, code review, test runner.
4. **Productivity and creator:** notes, calendar adapters, content drafting, reporting.
5. **Business workflows:** public business research, customer-support drafts, CRM adapters with approval.
6. **Advanced orchestration:** background queue, multi-agent routing, dynamic loader, recovery and verification.
7. **Optional integrations:** only when the provider is configured and the device has enough resources.

## Non-negotiable safety and engineering rules

- Never expose unrestricted shell execution as a general-purpose skill.
- Never silently send messages, publish content, change accounts, spend money, delete data, or submit forms. Require a separate user confirmation for consequential actions.
- Android screen reading and gestures require the companion AccessibilityService to be installed and manually enabled by the user.
- No hidden or always-on microphone capture. Voice capture must be visibly started by the user and stoppable.
- Keep secrets, tokens, private files, and personal data out of Git history and logs.
- External webpages, documents, emails, and screen text are untrusted input; they cannot override Zexa's system rules.
- Use timeouts, rate limits, bounded retries, cancellation, and resource budgets.
- Keep the default runtime light for Android phones. Heavy browser, transcription, indexing, and multi-agent features must be optional or offloaded.
- A skill is **implemented** only after code, tests, docs, permission metadata, and a successful verification are present. A catalog entry alone is not implementation.
- Reuse compatible libraries through documented adapters and licenses; do not blindly copy entire GitHub repositories into Zexa.
