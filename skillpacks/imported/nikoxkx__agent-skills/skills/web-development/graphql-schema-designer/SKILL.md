---
name: graphql-schema-designer
description: Designs GraphQL schemas with types, queries, mutations, subscriptions, and resolvers. Use when building or refactoring a GraphQL API.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: graphql, schema, types, resolvers, dataloader, pagination, federation
---

## Overview

Designs complete, production-ready GraphQL schemas including type definitions (scalar, object, input, enum, interface, union), queries, mutations, subscriptions, resolver patterns, solutions to the N+1 problem (DataLoader), pagination (cursor-based), error handling via union types or extensions, and guidance on schema-first vs code-first, stitching vs federation.

## When to Use This Skill

- Building a new GraphQL API or refactoring an existing one.
- User describes data model or operations ("users can query their orders with line items and status history").
- Choosing between REST and GraphQL or improving an existing GraphQL schema.

## Prerequisites

- GraphQL server (Apollo Server, Yoga, Pothos, Nexus, or codegen-based).
- Database or data sources the resolvers will call.
- For advanced: DataLoader, Redis for caching, understanding of federation.

## Steps

1. **Schema-first vs code-first decision**:
   - Schema-first: SDL + resolvers (good for collaboration with frontend).
   - Code-first: TypeScript classes/decorators or builder (better DX, type safety).

2. **Core type system**:
   - Scalars (ID, String, Int, Float, Boolean, custom DateTime, JSON).
   - Enums for status fields.
   - Input types for mutations.
   - Interfaces and unions for polymorphism.

3. **Query design**:
   - Root queries should be specific (not generic "node" unless using Relay).
   - Always think about what the client actually needs (avoid over-fetching by design).

4. **N+1 problem & DataLoader**:
   - Identify batchable loads (e.g., user for each post).
   - Create DataLoader per type.
   - Use in resolvers: `loader.load(id)`.

5. **Pagination**:
   - Prefer cursor-based (Relay connection spec or simple `after` + `first`).
   - Provide `edges` + `pageInfo` or a simpler `items` + `hasMore`.
   - Offset pagination only for admin/internal use cases.

6. **Mutations & input validation**:
   - One mutation per action.
   - Return the mutated entity or a payload type.
   - Use input objects.

7. **Error handling**:
   - Use union error types (e.g., `CreatePostResult = Post | ValidationError | Unauthorized`).
   - Or GraphQL errors with extensions.

8. **Subscriptions** (real-time):
   - Use `graphql-ws` or Apollo subscriptions.
   - Pub/sub backend (Redis, in-memory for dev).

9. **Output**:
   - Complete SDL or code-first schema.
   - Resolver map or class.
   - DataLoader setup example.
   - Pagination helper.
   - Example queries/mutations in the response.

## Examples

Full schema for a blog + comments + users (with DataLoader, cursor pagination, and union error types) is provided, along with resolver skeleton and subscription example.

## Edge Cases & Error Handling

- **Circular references**: Use lazy loading or interfaces.
- **Authorization**: Perform auth checks inside resolvers or with middleware/directives.
- **Rate limiting & complexity**: Use graphql-query-complexity or persisted queries.
- **Schema evolution**: Deprecate fields instead of removing; use versioning or federation for major changes.

## Verification

1. Load the schema in GraphQL Playground / Apollo Studio / Insomnia.
2. Run example queries and mutations — they return expected shapes.
3. Enable DataLoader batching and confirm single DB query for lists.
4. Test pagination cursors with real data.
5. Subscriptions fire on mutation.
6. Success: Schema is expressive, performant (no N+1), type-safe on both sides, and easy to evolve.

## References

- [GraphQL.js](https://graphql.org/graphql-js/)
- [Apollo Server](https://www.apollographql.com/docs/apollo-server/)
- [Relay Cursor Connections Spec](https://relay.dev/graphql/connections.htm)
- [DataLoader](https://github.com/graphql/dataloader)
- [Pothos GraphQL](https://pothos-graphql.dev/) or [Nexus](https://nexusjs.org/)
- [GraphQL Error Best Practices](https://www.apollographql.com/docs/apollo-server/data/errors/)
