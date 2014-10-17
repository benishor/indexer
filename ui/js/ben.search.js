function humanFileSize(bytes, si) {
    var thresh = si ? 1000 : 1024;
    if(bytes < thresh) return bytes + ' B';
    var units = si ? ['kB','MB','GB','TB','PB','EB','ZB','YB'] : ['KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(bytes >= thresh);
    return bytes.toFixed(1)+' '+units[u];
};

function humanDate(epochMilliseconds) {
	var date = new Date(parseInt(epochMilliseconds));
	var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	return date.getDay() + ' ' + months[date.getMonth()] + ' ' + date.getFullYear() + ' ' + date.getHours() + ':' + date.getMinutes(); 
}

function htmlEncode(text) {
	return $('<div/>').text(text).html();
}

var BenSearch = {
	searcher : {
		vars : {},
		currentPage : 0,
		perPage : 10,
		keyword: '',

		performSearch : function() {
			var vars = {
				from: BenSearch.searcher.currentPage * BenSearch.searcher.perPage,
				size: BenSearch.searcher.perPage,
				fields: ["title", "author", "content_type", "filename", "basename", "dirname", "checksum", "filesize", "filetime"],
				query: { 
					multi_match: {
					    "query": BenSearch.searcher.keyword,
					    "fields": ["filename^2", "title^2", "dirname^2", "content"],
					    "type": "most_fields",
					    "fuzziness": 2,
					    "prefix_length": 1
					}
				},
				highlight: {
					pre_tags: ["<span class=\"highlight\">"],
					post_tags: ["</span>"],
					fields: {
						content: {},
						title: {},
						author: {},
						filename: {},
						dirname: {}
					}
				}
			};
			BenSearch.searcher.vars = vars;

			$.ajax({
				url: 'http://localhost:9200/documents/_search?pretty=true',
				type: 'POST',
				crossDomain: true,
				dataType: 'json',
				data: JSON.stringify(vars),
				async: true,
				success: function(data) {
					BenSearch.renderer.renderResults(vars, data);
				}
			});			
		},

		search : function(keyword) {
			BenSearch.searcher.keyword = keyword;
			BenSearch.searcher.currentPage = 0;			
			BenSearch.searcher.performSearch();
		},

		nextPage : function(keyword) {
			BenSearch.searcher.currentPage = BenSearch.searcher.currentPage + 1;
			BenSearch.searcher.performSearch();
		},

		prevPage : function(keyword) {
			BenSearch.searcher.currentPage = BenSearch.searcher.currentPage - 1;
			BenSearch.searcher.performSearch();
		}
	},

	init : function() {
		$('#search').focus(function() {
			$('.result-selected').removeClass('result-selected');
		}).focus();

		$('.stats-page-next').off('click').click(function() {
			BenSearch.searcher.nextPage();
			return false;
		});

		$('.stats-page-prev').off('click').click(function() {
			BenSearch.searcher.prevPage();
			return false;
		});

			$(document).keydown(function(e) {
				var keyCode = e.keyCode || e.which;
				if (e.target.id != 'search') {
					switch (keyCode) {
						case 37: // left
							if ($('a.stats-page-prev:first').is(':visible')) {
								$('a.stats-page-prev:first').click();
							}
							break;
						case 39: // right
							if ($('a.stats-page-next:first').is(':visible')) {
								$('a.stats-page-next:first').click();
							}
							break;
						case 38: // up
							if ($('.result-selected').prev('.result-holder').length > 0) {
	 							$('.result-selected').removeClass('result-selected').prev('.result-holder').addClass('result-selected').find('.result-title a').focus();
 							} else {
 								$('.result-selected').removeClass('result-selected');
 								$('#search').focus();
 							}
							e.preventDefault();
							break;
						case 40: // down
							if ($('.result-selected').length > 0) {
								if ($('.result-selected').next('.result-holder').length > 0) {
									$('.result-selected').removeClass('result-selected').next('.result-holder').addClass('result-selected').find('.result-title a').focus();
								}
							} else {
								$('.result-holder:first').addClass('result-selected').focus();
							}
							e.preventDefault();
							break;
						case 191: // slash
							$('#search').focus().select();
							e.preventDefault();
							break;
					}
				}
			});

			$('#search').keydown(function(e) {
				var keyCode = e.keyCode || e.which;
				switch (keyCode) {
					case 38: // up
						break;
					case 40: // down
						if ($('.result-selected').length == 0) {
							var results = $('.result-holder');
							if (results.length > 0)
								$(results[0]).addClass('result-selected');
								$('.result-title a', results[0]).focus();
								e.preventDefault();
						}
						break;
					case 13:
						if ($(this).val() == '') {
							$('#results').empty();
						} else {
							BenSearch.searcher.search($(this).val())
						}
						break;
				}
			});
	},

	renderer : {
		renderHit : function(hit) {
			$result = $('.resultTemplate').clone().removeClass('resultTemplate');

			var title = (hit.highlight && hit.highlight.filename) ? hit.highlight.filename : htmlEncode(hit.fields.filename);
			if (hit.fields["content.title"] != undefined && hit.fields["content.title"] != '')
				title = (hit.highlight && hit.highlight["title"]) ? hit.highlight["title"] : htmlEncode(hit.fields["content.title"]);

			var $link = $('<a>').html(title).attr('href', 'http://localhost/books' + hit.fields.dirname + hit.fields.filename).attr('target', '_blank');

			$('.result-title', $result).append($link);
			$('.result-filename', $result).html((hit.highlight && hit.highlight.filename) ? hit.highlight.filename : htmlEncode(hit.fields.filename));
			$('.result-dirname', $result).html((hit.highlight && hit.highlight.dirname) ? hit.highlight.dirname : htmlEncode(hit.fields.dirname));
			$('.result-filesize', $result).text(humanFileSize(hit.fields.filesize));
			$('.result-filetime', $result).text(humanDate(hit.fields.filetime));

			return $result;
		},

		renderResults : function(searchVars, result) {
			$('#results').empty();
			for (var i in result.hits.hits) {
				$('#results').append(BenSearch.renderer.renderHit(result.hits.hits[i]));
			}

			var from = BenSearch.searcher.vars.from;
			var to = result.hits.hits.length + from;
			var prevPage = BenSearch.searcher.currentPage ? BenSearch.searcher.currentPage - 1 : 0;
			var nextPage = BenSearch.searcher.currentPage ? BenSearch.searcher.currentPage + 1 : 1;

			if (result.hits.total > 0) {
				$('.stats-count').text('Displaying records ' + from + '-' + to + ' out of ' + result.hits.total);
				$('.stats').show();
			} else {
				$('.stats-count').text('No matching records found.');
				$('.stats').show();
				$('.stats:eq(1)').hide();
			}

			if (from > 0)
				$('.stats-page-prev').show();
			else
				$('.stats-page-prev').hide();

			if ((result.hits.total - to) > 1)
				$('.stats-page-next').show();
			else
				$('.stats-page-next').hide();

			// if search field not focused, focus first result. we might have used kbd navigation
			if (!$('#search').is(':focus')) {
				$('.result-holder:first').addClass('result-selected').focus();
			}

		}
	}
}
