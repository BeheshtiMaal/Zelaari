import type { Question, QuestionRecord, QuestionSelection as WireSelection } from "./protocol";
export type QuestionSelection = Omit<WireSelection, "option_ids"> & { option_ids: string[] };

export function initialSelection(question: Question): QuestionSelection {
  return { question_id: question.id, option_ids: question.type === "rank" ? question.options.map(option => option.id) : [], other: null, hint: null };
}
export function validSelection(question: Question, selection: QuestionSelection): boolean {
  const ids = selection.option_ids ?? [], other = !!selection.other?.trim();
  if (selection.other !== null && selection.other !== undefined && !other) return false;
  if (new Set(ids).size !== ids.length || ids.some(id => !question.options.some(option => option.id === id))) return false;
  if (question.type === "single") return ids.length + Number(other) === 1;
  if (question.type === "multi") return ids.length > 0 || other;
  return ids.length === question.options.length;
}
export function chooseOption(question: Question, selection: QuestionSelection, id: string): QuestionSelection {
  if (question.type === "rank") return selection;
  if (question.type === "single") return { ...selection, option_ids: [id], other: null, hint: null };
  const ids = selection.option_ids ?? [];
  return { ...selection, option_ids: ids.includes(id) ? ids.filter(value => value !== id) : [...ids, id] };
}
export function rankMove(selection: QuestionSelection, id: string, direction: -1 | 1): QuestionSelection {
  const ids = [...(selection.option_ids ?? [])], index = ids.indexOf(id), target = index + direction;
  if (index < 0 || target < 0 || target >= ids.length) return selection;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  return { ...selection, option_ids: ids };
}
export function rankDrop(selection: QuestionSelection, id: string, target: string): QuestionSelection {
  const ids = [...(selection.option_ids ?? [])], from = ids.indexOf(id), to = ids.indexOf(target);
  if (from < 0 || to < 0) return selection;
  ids.splice(from, 1); ids.splice(to, 0, id);
  return { ...selection, option_ids: ids };
}
export function answeredSummary(record: QuestionRecord) {
  return record.request.questions.map(question => {
    const answer = record.answer?.answers?.find(answer => answer.question_id === question.id);
    const values = (answer?.option_ids ?? []).map(id => question.options.find(option => option.id === id)?.label ?? id);
    if (answer?.other) values.push(answer.other);
    if (answer?.hint) values.push(answer.hint);
    return { id: question.id, text: question.text, values: values.join(question.type === "rank" ? " → " : ", ") };
  });
}
