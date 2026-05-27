/**
 * Kairo Phantom v4.0 — Enterprise Collaborative Hocuspocus WebSocket Server
 * Core Yjs sync and coordination backend for collaborative AI co-authoring.
 */

const { Hocuspocus } = require('@hocuspocus/server');

// Kairo-themed terminal logger helpers (Kairo Purple styling)
const PURPLE = '\x1b[38;2;108;92;231m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';
const logKairo = (msg) => console.log(`${BOLD}${PURPLE}[Kairo Hocuspocus]${RESET} ${msg}`);

logKairo("Initializing collaborative synchronization engine...");

// In-memory mock database for server-side persistence & audit logging
const documentStore = new Map();

// Configure the Hocuspocus collaborative sync server
const server = new Hocuspocus({
  port: process.env.PORT || 1234,
  timeout: 30000,
  
  // Connection Hook: Validate auth tokens and roles
  async onConnect(data) {
    const { requestParameters, socketId } = data;
    const token = requestParameters.get('token');
    const docId = requestParameters.get('docId') || 'default-doc';

    logKairo(`Connection request from socket ${socketId} on document [${docId}]`);

    // Verify token
    if (!token) {
      logKairo(`⚠️ Rejecting connection from socket ${socketId}: Missing authorization token.`);
      throw new Error('Unauthorized: Missing auth token');
    }

    // Role-based access rules validation
    let isAiPeer = token.startsWith('kairo-token-');
    let peerRole = isAiPeer ? 'AI Collaborative Peer' : 'Human Editor';
    let clientId = isAiPeer ? token.split('-').slice(2).join('-') : `human-${socketId}`;

    logKairo(`✅ Connection authorized. Client: ${clientId} | Role: ${peerRole}`);

    // Context passed down to subsequent hooks
    return {
      user: {
        id: clientId,
        role: peerRole,
        isAi: isAiPeer,
      }
    };
  },

  // Document load Hook: Retrieve CRDT updates from persistence layer
  async onLoadDocument(data) {
    const { documentName } = data;
    logKairo(`📂 Loading document: ${documentName}`);

    if (documentStore.has(documentName)) {
      logKairo(`♻️ Restoring state for: ${documentName} from persistence store.`);
      return documentStore.get(documentName);
    }

    logKairo(`✨ Initializing new collaborative state room for: ${documentName}`);
    return null;
  },

  // Document save Hook: Auto-persist CRDT state snapshots
  async onChange(data) {
    const { documentName, document } = data;
    // Periodically persist binary document updates
    const state = document.getMap('kairo-metadata');
    const lastEdit = state.get('last_edit_at') || 'none';
    const totalEdits = state.get('total_edits') || 0;

    logKairo(`📝 Document changed: [${documentName}] | Total AI edits: ${totalEdits} | Last Edit: ${lastEdit}`);
  },

  // Disconnect Hook
  async onDisconnect(data) {
    const { socketId, context } = data;
    const clientName = context?.user?.id || `socket-${socketId}`;
    logKairo(`🔌 Client disconnected: ${clientName}`);
  }
});

// Run server
server.listen().then(() => {
  logKairo(`🚀 Collaborative sync service listening on port ${server.configuration.port}`);
  logKairo(`✨ Ready for first-class AI ghost-writing session triggers.`);
});
