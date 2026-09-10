function selectedPath(file) {
  return file.webkitRelativePath || file.name;
}

function matchesRequestedPath(selected, requested) {
  return (
    selected === requested ||
    requested.endsWith(`/${selected}`) ||
    selected.endsWith(`/${requested}`)
  );
}

export function activeCorrectionTasks(reviewCase) {
  return (reviewCase?.tasks || []).filter((task) => task.status !== 'accepted');
}

export function findMissingCorrectionFiles(reviewCase, selectedFiles = []) {
  if (!reviewCase) return [];
  const selectedPaths = selectedFiles.map(selectedPath);
  return activeCorrectionTasks(reviewCase)
    .filter(
      (task) =>
        !selectedPaths.some((path) => matchesRequestedPath(path, task.filename))
    )
    .map((task) => task.filename);
}
