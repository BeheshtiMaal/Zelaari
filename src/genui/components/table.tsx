"use client";
import { genuiCopy } from "../../i18n/genui";
import { currentLocale } from "../../lib/locale";

/** Display-only table. Cells keep their own direction so a path and a sentence can share a row. */
export function TableView({ columns, rows }: { columns: string[]; rows: string[][] }) {
  const t = genuiCopy(currentLocale());
  return <div className="genui-table-wrap">
    <table className="genui-table" data-testid="genui-table" aria-label={t.table}>
      <thead><tr>{columns.map((column, index) => <th key={index} scope="col" dir="auto">{column}</th>)}</tr></thead>
      <tbody>
        {rows.map((row, rowIndex) => <tr key={rowIndex}>
          {columns.map((_, columnIndex) => <td key={columnIndex} dir="auto">{row[columnIndex] ?? ""}</td>)}
        </tr>)}
      </tbody>
    </table>
  </div>;
}
