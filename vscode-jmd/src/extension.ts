import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';

let previewPanel: vscode.WebviewPanel | undefined;

export function activate(context: vscode.ExtensionContext) {
    // Register the preview command
    const previewCommand = vscode.commands.registerCommand('jmd.openPreview', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('Open a .jmd file first');
            return;
        }
        if (!editor.document.fileName.endsWith('.jmd')) {
            vscode.window.showInformationMessage('Not a .jmd file');
            return;
        }
        openPreview(context, editor.document);
    });

    // Tree data provider for annotations
    const treeProvider = new JMDAnnotationProvider();
    const treeView = vscode.window.registerTreeDataProvider('jmdAnnotations', treeProvider);

    // Refresh tree when document changes
    const onChange = vscode.workspace.onDidChangeTextDocument((e) => {
        if (e.document.fileName.endsWith('.jmd')) {
            treeProvider.refresh(e.document);
            if (previewPanel) {
                updatePreview(e.document);
            }
        }
    });

    // Refresh tree when switching editors
    const onSwitch = vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor && editor.document.fileName.endsWith('.jmd')) {
            treeProvider.refresh(editor.document);
        }
    });

    context.subscriptions.push(previewCommand, treeView, onChange, onSwitch);
}

function openPreview(context: vscode.ExtensionContext, document: vscode.TextDocument) {
    const column = vscode.ViewColumn.Two;

    if (previewPanel) {
        previewPanel.reveal(column);
    } else {
        previewPanel = vscode.window.createWebviewPanel(
            'jmdPreview',
            'JMD Preview',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );
        previewPanel.onDidDispose(() => {
            previewPanel = undefined;
        });
    }

    updatePreview(document);
}

function updatePreview(document: vscode.TextDocument) {
    if (!previewPanel) return;

    const filePath = document.fileName;
    const tmpFile = path.join(require('os').tmpdir(), `jmd-preview-${Date.now()}.html`);

    const child = spawn('jmd', ['render', filePath, '-f', 'html', '-o', tmpFile], {
        shell: true,
    });

    child.on('close', (code) => {
        if (code === 0 && fs.existsSync(tmpFile)) {
            const html = fs.readFileSync(tmpFile, 'utf-8');
            previewPanel!.webview.html = html;
            try { fs.unlinkSync(tmpFile); } catch {}
        } else {
            previewPanel!.webview.html = '<p style="color:red">Failed to render preview. Is <code>jmd</code> installed?</p>';
        }
    });
}

// ─── Annotation Tree Provider ───

class JMDAnnotationProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChange = new vscode.EventEmitter<vscode.TreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChange.event;

    private currentDocument: vscode.TextDocument | undefined;

    refresh(document?: vscode.TextDocument) {
        this.currentDocument = document || this.currentDocument;
        this._onDidChange.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: vscode.TreeItem): Thenable<vscode.TreeItem[]> {
        if (!this.currentDocument) {
            return Promise.resolve([]);
        }

        const text = this.currentDocument.getText();
        const unresolved = this._extractAnnotations(text, false);
        const resolved = this._extractAnnotations(text, true);

        if (!element) {
            // Root level: show counts
            const items: vscode.TreeItem[] = [];
            if (unresolved.length > 0) {
                const item = new vscode.TreeItem(`Unresolved (${unresolved.length})`, vscode.TreeItemCollapsibleState.Expanded);
                item.iconPath = new vscode.ThemeIcon('error');
                items.push(item);
            }
            if (resolved.length > 0) {
                const item = new vscode.TreeItem(`Resolved (${resolved.length})`, vscode.TreeItemCollapsibleState.Collapsed);
                item.iconPath = new vscode.ThemeIcon('check');
                items.push(item);
            }
            return Promise.resolve(items);
        }

        // Child level: individual annotations
        const isResolved = element.label?.toString().startsWith('Resolved');
        const list = isResolved ? resolved : unresolved;

        return Promise.resolve(list.map((a) => {
            const item = new vscode.TreeItem(a.id, vscode.TreeItemCollapsibleState.None);
            item.description = `[${a.type}] ${a.text.substring(0, 40)}${a.text.length > 40 ? '...' : ''}`;
            item.tooltip = a.text;
            item.iconPath = new vscode.ThemeIcon(
                a.type === 'question' ? 'question' :
                a.type === 'praise' ? 'star' :
                a.type === 'critique' ? 'warning' :
                a.type === 'rewrite' ? 'edit' :
                a.type === 'lore-check' ? 'book' :
                'comment'
            );
            item.command = {
                command: 'jmd.jumpToAnnotation',
                title: 'Jump to Annotation',
                arguments: [a.id],
            };
            return item;
        }));
    }

    private _extractAnnotations(text: string, resolved: boolean): Array<{id: string, type: string, text: string}> {
        const results: Array<{id: string, type: string, text: string}> = [];
        const sectionMatch = text.match(/@annotations\s*\n([\s\S]*?)(?=\n@\w+|\s*$)/);
        if (!sectionMatch) return results;

        const section = sectionMatch[1];
        // Parse annotation blocks: id:\n  type: ...\n  status: ...\n  text: ...
        const blocks = section.split(/\n(?=[a-zA-Z0-9_-]+:\s*$)/);
        for (const block of blocks) {
            const idMatch = block.match(/^([a-zA-Z0-9_-]+):/);
            if (!idMatch) continue;
            const id = idMatch[1];
            const typeMatch = block.match(/type:\s*(.+)/);
            const statusMatch = block.match(/status:\s*(.+)/);
            const textMatch = block.match(/text:\s*["']?(.+)/);

            const status = statusMatch ? statusMatch[1].trim() : 'unresolved';
            if ((resolved && status === 'resolved') || (!resolved && status !== 'resolved')) {
                results.push({
                    id,
                    type: typeMatch ? typeMatch[1].trim() : 'note',
                    text: textMatch ? textMatch[1].trim().replace(/["']$/, '') : '',
                });
            }
        }
        return results;
    }
}
