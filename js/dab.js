/**
* DAB game
*/

var global_timeout = 30000;

function random_int (min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function keys(obj) {
    var ret = [];
    for(var k in obj) {
        if (obj.hasOwnProperty(k)) {
            ret.push(k);
        }
    }
    return ret;
}

function do_query(url, complete_callback, kwargs) {
    var all_kwargs = {
        url: url,
        type: 'get',
        dataType: 'jsonp',
        timeout: global_timeout, // TODO: convert to setting. Necessary to detect jsonp error.
        success: function(data) {
            console.log('successful ajax query to ' + url);
            complete_callback(null, data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log('failed query to ' + url);
            complete_callback(errorThrown, null);
        },
        complete: function(jqXHR, textStatus) {
            // TODO: error handling (jsonp doesn't get error() calls for a lot of errors)
        },
        headers: { 'User-Agent': 'DABble/0.0.0 stephen laporte stephen.laporte@gmail.com' }
    };

    for (var key in kwargs) {
        if(kwargs.hasOwnProperty(key)) {
            all_kwargs[key] = kwargs[key];
        }
    }
    $.ajax(all_kwargs);
}

function dab(title) {
	var title_fm = title.replace('_', ' ');
	var choices, 
		found_string;

	function process_backlinks(err, data) {
		var links = data['query']['backlinks'];
		var page_id = keys(data['query']['pages']);
		var dab_content = data['query']['pages'][page_id]['revisions']['0']['*'];
		var dabs;
		var pages = [];
		for(var i = 0; i < links.length; i++) {
			if(links[i].ns === 0){
				pages.push(links[i].pageid);
			}
		}

		choices = dab_content.match(/\*.*\n/gi);
		
		choose_page(err, pages);
	}

	function process_page(err, data, num) {
		var page_id = keys(data['query']['pages']);
		var page_content = data['query']['pages'][page_id]['revisions']['0']['*'];
		var pattern = '(?:[^\s\r\n]*[\s\r\n]+){0,10}(?:[^\s\r\n]*)' + title_fm.toLowerCase() + '(?:[^\s\r\n]*)(?:[\s\r\n]+[^\s\r\n]*){0,7}';
		found_string = page_content.toLowerCase().match(pattern);
		found_string = found_string[0]; // TODO: trim down that punctation		
		
		console.log('found ' + title_fm + ' in ' + data['query']['pages'][page_id]['title'])
		render();
	}

	function choose_page(err, pages) {
		var num = random_int(0, pages.length - 1);
		var page = pages[num];
		var page_content = do_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&pageids=' + page + '&rvprop=content&format=json', process_page);
		console.log('loading pageid ' + page + '');
	}

	function render(err) {
		$(document).ready(function() {
			$('#phrase').html('<p><em>In the phrase</em></p><p>' + found_string + '</p>');
			$('#inst').html('<p><em>Does ' + title_fm + ' mean</em></p>');
			for(var i = 0; i < choices.length; i++) {
				$('#as').append('<li>' + choices[i] + '</li>');
			}
			console.log('prepared html');
		});
	}

	do_query('http://en.wikipedia.org/w/api.php?action=query&list=backlinks&bltitle=' + title + '&prop=revisions&titles=' + title + '&rvprop=content&bllimit=500&format=json', process_backlinks);
}

var a = new dab('Animal_behaviour');
