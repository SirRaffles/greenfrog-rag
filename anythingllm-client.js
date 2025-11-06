/**
 * AnythingLLM Document Upload & Embedding Client (JavaScript/Node.js)
 *
 * A Node.js client for the AnythingLLM API that handles the complete
 * document workflow: upload → embed.
 *
 * Requirements:
 *   - Node.js 14+
 *   - fetch API (Node 18+) or axios/node-fetch for older versions
 *
 * Usage:
 *   const client = new AnythingLLMClient({
 *     baseUrl: "http://localhost:3001",
 *     apiKey: "sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"
 *   });
 *
 *   const result = await client.uploadAndEmbed(
 *     "/path/to/document.pdf",
 *     "greenfrog"
 *   );
 *   console.log(result);
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

/**
 * Log levels
 */
const LogLevel = {
  DEBUG: 1,
  INFO: 2,
  WARNING: 3,
  ERROR: 4
};

/**
 * AnythingLLM API Client
 */
class AnythingLLMClient {
  /**
   * Initialize the client
   *
   * @param {Object} options - Configuration options
   * @param {string} options.baseUrl - Base URL of AnythingLLM instance
   * @param {string} options.apiKey - API authentication key
   * @param {number} options.logLevel - Logging verbosity (see LogLevel)
   * @param {number} options.timeout - Request timeout in milliseconds
   */
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || 'http://localhost:3001').replace(/\/$/, '');
    this.apiKey = options.apiKey || '';
    this.logLevel = options.logLevel || LogLevel.INFO;
    this.timeout = options.timeout || 30000;

    this.log(LogLevel.INFO, `Initializing AnythingLLM client: ${this.baseUrl}`);
  }

  /**
   * Log message based on log level
   * @private
   */
  log(level, message) {
    if (level >= this.logLevel) {
      const prefix = {
        [LogLevel.DEBUG]: '[DEBUG]',
        [LogLevel.INFO]: '[INFO]',
        [LogLevel.WARNING]: '[WARNING]',
        [LogLevel.ERROR]: '[ERROR]'
      }[level];

      const stream = level === LogLevel.ERROR ? process.stderr : process.stdout;
      stream.write(`${prefix} ${message}\n`);
    }
  }

  /**
   * Make HTTP request to AnythingLLM API
   * @private
   */
  async request(method, endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;

    this.log(LogLevel.DEBUG, `${method} ${endpoint}`);

    const fetchOptions = {
      method,
      timeout: this.timeout,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        ...options.headers
      }
    };

    // Handle different body types
    if (options.body) {
      if (options.body instanceof FormData) {
        // FormData: don't set Content-Type, let fetch handle it
        fetchOptions.body = options.body;
      } else if (typeof options.body === 'object') {
        // JSON: set header and stringify
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(options.body);
      } else {
        // String or other
        fetchOptions.body = options.body;
      }
    }

    try {
      const response = await fetch(url, fetchOptions);
      const contentType = response.headers.get('content-type');

      let data;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      this.log(LogLevel.DEBUG, `Response status: ${response.status}`);

      return {
        status: response.status,
        data: data,
        headers: response.headers
      };
    } catch (error) {
      this.log(LogLevel.ERROR, `Request failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Upload document to AnythingLLM storage
   *
   * This is Step 1 of the workflow. The document is converted to text
   * and stored in custom-documents/ folder.
   *
   * @param {string} filePath - Path to document file to upload
   * @returns {Promise<string>} Document location (e.g., "custom-documents/filename.txt")
   * @throws {Error} If file doesn't exist or upload fails
   */
  async uploadDocument(filePath) {
    const resolvedPath = path.resolve(filePath);

    if (!fs.existsSync(resolvedPath)) {
      throw new Error(`File not found: ${resolvedPath}`);
    }

    const fileName = path.basename(resolvedPath);
    this.log(LogLevel.INFO, `Uploading document: ${fileName}`);

    // Create FormData with file
    const formData = new FormData();
    formData.append('file', fs.createReadStream(resolvedPath));

    const response = await this.request(
      'POST',
      '/api/v1/document/upload',
      {
        body: formData,
        headers: {} // FormData handles Content-Type
      }
    );

    this.log(LogLevel.DEBUG, `Upload response: ${JSON.stringify(response.data, null, 2)}`);

    if (response.status !== 200 && response.status !== 201) {
      throw new Error(
        `Upload failed with status ${response.status}: ${JSON.stringify(response.data)}`
      );
    }

    // Extract document location
    if (response.data.document && response.data.document.location) {
      const location = response.data.document.location;
      this.log(LogLevel.INFO, `Document uploaded: ${location}`);
      return location;
    } else {
      throw new Error(`Unexpected response format: ${JSON.stringify(response.data)}`);
    }
  }

  /**
   * Embed documents in workspace
   *
   * This is Step 2 of the workflow. Documents are chunked and vectors
   * are created and stored in the vector database.
   *
   * @param {string} workspaceSlug - Workspace slug/identifier
   * @param {string[]} documentPaths - List of document paths
   * @returns {Promise<Object>} Embedding result object
   * @throws {Error} If embedding fails
   */
  async embedInWorkspace(workspaceSlug, documentPaths) {
    this.log(
      LogLevel.INFO,
      `Embedding ${documentPaths.length} document(s) in workspace: ${workspaceSlug}`
    );

    const payload = { adds: documentPaths };

    const response = await this.request(
      'POST',
      `/api/v1/workspace/${workspaceSlug}/update-embeddings`,
      {
        body: payload,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      }
    );

    this.log(LogLevel.DEBUG, `Embed response: ${JSON.stringify(response.data, null, 2)}`);

    const result = {
      success: response.status === 200 || response.status === 201,
      status: response.status,
      raw: response.data
    };

    if (result.success) {
      if (response.data.workspace) {
        result.workspace = response.data.workspace;
      }
      result.message = response.data.message || 'Embedded successfully';
      this.log(LogLevel.INFO, result.message);
    } else {
      result.message = response.data.message || `Failed with status ${response.status}`;
      this.log(LogLevel.ERROR, result.message);
    }

    return result;
  }

  /**
   * Complete workflow: Upload and embed document
   *
   * @param {string} filePath - Path to document to upload
   * @param {string} workspaceSlug - Workspace to embed document in
   * @param {number} waitBeforeEmbed - Milliseconds to wait between upload and embed
   * @returns {Promise<Object>} Result object with upload and embed results
   */
  async uploadAndEmbed(filePath, workspaceSlug, waitBeforeEmbed = 1000) {
    const fileName = path.basename(filePath);
    this.log(
      LogLevel.INFO,
      `Starting upload and embed workflow for: ${fileName}`
    );

    const result = {
      upload: null,
      embed: null,
      success: false
    };

    try {
      // Step 1: Upload
      const location = await this.uploadDocument(filePath);
      result.upload = {
        success: true,
        location: location,
        file: fileName
      };

      // Wait for file processing
      if (waitBeforeEmbed > 0) {
        this.log(
          LogLevel.INFO,
          `Waiting ${waitBeforeEmbed}ms for file processing...`
        );
        await new Promise(resolve => setTimeout(resolve, waitBeforeEmbed));
      }

      // Step 2: Embed
      result.embed = await this.embedInWorkspace(workspaceSlug, [location]);

      result.success = result.upload.success && result.embed.success;
    } catch (error) {
      this.log(LogLevel.ERROR, `Workflow failed: ${error.message}`);
      result.error = error.message;
    }

    return result;
  }

  /**
   * Upload and embed multiple documents
   *
   * @param {string[]} filePaths - List of file paths to upload
   * @param {string} workspaceSlug - Workspace to embed documents in
   * @param {number} waitBeforeEmbed - Milliseconds to wait before embedding all
   * @returns {Promise<Object>} Result from embedding all documents
   */
  async uploadMultiple(filePaths, workspaceSlug, waitBeforeEmbed = 2000) {
    this.log(LogLevel.INFO, `Uploading ${filePaths.length} document(s)...`);

    const locations = [];
    const result = {
      uploads: [],
      embed: null,
      success: false
    };

    for (const filePath of filePaths) {
      try {
        const location = await this.uploadDocument(filePath);
        locations.push(location);
        result.uploads.push({
          file: path.basename(filePath),
          location: location,
          success: true
        });
      } catch (error) {
        this.log(LogLevel.WARNING, `Failed to upload ${filePath}: ${error.message}`);
        result.uploads.push({
          file: path.basename(filePath),
          success: false,
          error: error.message
        });
      }
    }

    if (locations.length === 0) {
      result.error = 'No documents uploaded successfully';
      return result;
    }

    this.log(LogLevel.INFO, `Waiting ${waitBeforeEmbed}ms before embedding...`);
    await new Promise(resolve => setTimeout(resolve, waitBeforeEmbed));

    result.embed = await this.embedInWorkspace(workspaceSlug, locations);
    result.success = locations.length > 0 && result.embed.success;

    return result;
  }

  /**
   * Get workspace information
   *
   * @param {string} workspaceSlug - Workspace slug/identifier
   * @returns {Promise<Object|null>} Workspace info or null if failed
   */
  async getWorkspaceInfo(workspaceSlug) {
    this.log(LogLevel.INFO, `Fetching workspace info: ${workspaceSlug}`);

    const response = await this.request('GET', `/api/v1/workspace/${workspaceSlug}`);

    if (response.status === 200) {
      return response.data;
    } else {
      this.log(LogLevel.ERROR, `Failed to get workspace: ${JSON.stringify(response.data)}`);
      return null;
    }
  }

  /**
   * Verify that a document is embedded in workspace
   *
   * @param {string} workspaceSlug - Workspace slug/identifier
   * @param {string} documentName - Document name to look for (without prefix)
   * @returns {Promise<boolean>} True if document found in workspace
   */
  async verifyDocumentEmbedded(workspaceSlug, documentName) {
    const workspace = await this.getWorkspaceInfo(workspaceSlug);

    if (!workspace) {
      return false;
    }

    // Check documents array
    if (workspace.documents) {
      for (const doc of workspace.documents) {
        if (doc.name && doc.name.includes(documentName)) {
          return true;
        }
        if (doc.location && doc.location.includes(documentName)) {
          return true;
        }
      }
    }

    return false;
  }
}

/**
 * Example usage
 */
async function exampleUsage() {
  // Initialize client
  const client = new AnythingLLMClient({
    baseUrl: 'http://localhost:3001',
    apiKey: 'sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA',
    logLevel: LogLevel.INFO
  });

  try {
    // Upload and embed single document
    console.log('\n=== Example 1: Upload and Embed Single Document ===\n');

    const result = await client.uploadAndEmbed(
      '/path/to/document.pdf',
      'greenfrog'
    );

    console.log('Result:', JSON.stringify(result, null, 2));

    // Verify document is embedded
    if (result.success) {
      const isEmbedded = await client.verifyDocumentEmbedded(
        'greenfrog',
        'document'
      );
      console.log('Document embedded:', isEmbedded);
    }

  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Export for use as module
module.exports = AnythingLLMClient;

// Run example if executed directly
if (require.main === module) {
  exampleUsage().catch(console.error);
}
