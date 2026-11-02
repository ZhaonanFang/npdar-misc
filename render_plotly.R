# Render the example plots to HTML for record_plotly.py.
# Usage: Rscript render_plotly.R [path/to/npdar] [build-dir]
args <- commandArgs(trailingOnly = TRUE)
pkg_dir <- if (length(args) >= 1) args[[1]] else file.path("..", "npdar")
build_dir <- if (length(args) >= 2) args[[2]] else "build"

dir.create(build_dir, showWarnings = FALSE, recursive = TRUE)
pkgload::load_all(pkg_dir, quiet = TRUE)

rc <- plot_raincloud_ly(iris,
                        x = "Sepal.Length",
                        y = "Species",
                        colors = c("#11A7F2", "#E00087", "#00bdaa"),
                        scatter_layout = "dots",
                        show_legend = TRUE) |>
  plotly::layout(yaxis = list(showticklabels = FALSE),
                 legend = list(x = 1, y = -0.2, xanchor = "right",
                               orientation = "h"))

cm <- plot_corrmat_ly(mtcars,
                      method = "spearman",
                      show_values = FALSE,
                      show_stars = TRUE,
                      colorbar = list(title = "Correlation")) |>
  plotly::layout(annotations = list(
    text = paste0("<i><b>Note:</b>",
                  "*: p<0.05, **: p<0.01, ***: p<0.001.</i>"),
    x = 1, y = 1, xref = "paper", yref = "paper",
    xanchor = "right", yanchor = "top",
    showarrow = FALSE))

# selfcontained = TRUE needs pandoc, so write the JS dependencies alongside
htmlwidgets::saveWidget(rc, file.path(build_dir, "raincloud.html"), selfcontained = FALSE)
htmlwidgets::saveWidget(cm, file.path(build_dir, "corrmat.html"), selfcontained = FALSE)
