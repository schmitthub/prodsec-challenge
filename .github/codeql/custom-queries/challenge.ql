/**
 * Placeholder that keeps the pack compiling. Replace the metadata and body
 * with the project's first custom query; the header below is what Code
 * scanning reads (id/name/severity/tags). `kind problem` = one alert per
 * selected element with a message; use `path-problem` for taint flows.
 *
 * @name Placeholder query
 * @description Selects nothing. Replaced by the first project-specific query.
 * @kind problem
 * @problem.severity warning
 * @security-severity 5.0
 * @precision medium
 * @id py/prodsec-challenge/placeholder
 * @tags security
 */

import python

from File f
where none()
select f, "placeholder"
