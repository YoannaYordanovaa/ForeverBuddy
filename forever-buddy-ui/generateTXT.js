import { readdirSync, readFileSync, writeFileSync, statSync } from 'fs';
import { join, extname } from 'path';

const EXTENSIONS = ['.js', '.jsx', '.ts', '.tsx', '.css', '.html', '.json'];
const IGNORE = ['node_modules', 'dist', '.git', 'generateTXT.js'];

function collectFiles(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (IGNORE.includes(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      collectFiles(full, files);
    } else if (EXTENSIONS.includes(extname(entry))) {
      files.push(full);
    }
  }
  return files;
}

const files = collectFiles('.');
let output = '';

for (const file of files) {
  output += `\n${'='.repeat(60)}\n`;
  output += `FILE: ${file}\n`;
  output += `${'='.repeat(60)}\n`;
  output += readFileSync(file, 'utf-8') + '\n';
}

writeFileSync('project_code.txt', output);
console.log(`✅ Готово! Записани ${files.length} файла в project_code.txt`);