/** @odoo-module **/

function addHeaderColumns(table) {
    if (!table) return;

    const thead = table.querySelector('thead');
    if (!thead) return;

    const rows = thead.querySelectorAll('tr');

    rows.forEach((row, rowIndex) => {
        // Idempotency check for this specific row
        if (row.querySelector('th.o_mis_kpi_vat_cc')) return;

        const ths = row.querySelectorAll('th');
        if (ths.length >= 1) {
            const firstTh = ths[0];

            // Copy classes from the first header
            const thClass = firstTh.getAttribute('class') || '';

            // Create VAT columns
            const ccTh = document.createElement('th');
            ccTh.className = "o_mis_kpi_vat_cc " + thClass;
            ccTh.textContent = "";

            const vatTh = document.createElement('th');
            vatTh.className = "o_mis_kpi_vat " + thClass;
            vatTh.textContent = "";

            // Copy styles
            const styleAttr = firstTh.getAttribute('style');
            if (styleAttr) {
                ccTh.setAttribute('style', styleAttr);
                vatTh.setAttribute('style', styleAttr);
            }

            // Insert after the first header
            firstTh.after(ccTh);
            ccTh.after(vatTh);
        }
    });
}

function processSingleTable(table) {
    if (!table) return;

    if (!table.classList.contains('o_mis_vat_processed')) {
        table.classList.add('o_mis_vat_processed');
    }

    addHeaderColumns(table);

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const tds = row.querySelectorAll('td');
        if (tds.length < 2) return;

        const descTd = tds[0];

        if (row.querySelector('td.o_mis_kpi_vat_cc')) return;

        const text = descTd.textContent.trim();
        let cc = '', num = '', name = text;

        let m = text.match(/^(.*)\s+\(([A-Za-z]{2})\s+([\d\-\s]+)\)$/);

        if (m) {
            name = m[1].trim();
            cc = m[2].toUpperCase();
            num = m[3].replace(/\s+/g, ' ').trim();
        } else {
            m = text.match(/^(.*)\s+\(([\d\-\s]+)\)$/);
            if (m) {
                name = m[1].trim();
                cc = '';
                num = m[2].replace(/\s+/g, ' ').trim();
            } else {
                m = text.match(/^(.*)\s+([A-Za-z]{2})\s+([\d\-\s]+)$/);
                if (m) {
                    name = m[1].trim();
                    cc = m[2].toUpperCase();
                    num = m[3].replace(/\s+/g, ' ').trim();
                }
            }
        }

        if (m) {
            descTd.textContent = name;
        }

        const styleAttr = descTd.getAttribute('style');
        const colorAttr = descTd.getAttribute('data-color');
        const cellClass = descTd.getAttribute('class') || '';

        const ccTd = document.createElement('td');
        ccTd.className = "o_mis_kpi_vat_cc " + cellClass;
        ccTd.textContent = cc;

        const numTd = document.createElement('td');
        numTd.className = "o_mis_kpi_vat " + cellClass;
        numTd.textContent = num;

        if (styleAttr) {
            ccTd.setAttribute('style', styleAttr);
            numTd.setAttribute('style', styleAttr);
        }

        if (colorAttr) {
            ccTd.setAttribute('data-color', colorAttr);
            numTd.setAttribute('data-color', colorAttr);
        }

        descTd.after(ccTd);
        ccTd.after(numTd);
    });
}

function processAllTables(rootElement) {
    try {
        if (!rootElement || !rootElement.querySelectorAll) return;

        const tables = rootElement.querySelectorAll('.o_mis_preview table, .o_mis_report_preview table, table.mis_builder');
        tables.forEach(table => processSingleTable(table));

    } catch (e) {
        console.error('MISPartnerVAT error', e);
    }
}

function initMisVatColumns() {
    console.log('MISPartnerVAT: Initializing observer...');

    let debounceTimer;

    const observer = new MutationObserver((mutations) => {
        const tablesToProcess = new Set();

        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== Node.ELEMENT_NODE) continue;

                if (node.matches && (node.matches('table.mis_builder') || node.matches('.o_mis_preview table') || node.matches('.o_mis_report_preview table'))) {
                    tablesToProcess.add(node);
                    continue;
                }

                if (node.querySelector) {
                    const containedTables = node.querySelectorAll('table.mis_builder');
                    if (containedTables.length > 0) {
                        containedTables.forEach(t => tablesToProcess.add(t));
                        continue;
                    }
                }

                const parentTable = node.closest('table.mis_builder');
                if (parentTable) {
                    tablesToProcess.add(parentTable);
                }
            }
        }

        if (tablesToProcess.size > 0) {
            if (debounceTimer) clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                tablesToProcess.forEach(table => processSingleTable(table));
            }, 10);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    processAllTables(document.body);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initMisVatColumns();
    });
} else {
    initMisVatColumns();
}
