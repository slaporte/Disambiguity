/**
* DAB game
*/

var global_timeout = 5000;
var retry_limit = 4; /* global retry number */

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
	var title_fm = title.replace(/_/g, ' ');
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
		if(page_content.match(/<ol><li>REDIRECT/gi)) {
			console.log('no redirects, please');
			redo(retry_limit);
		} else {
			var pattern = new RegExp('(?:[^\s\r\n]*[\s\r\n]+){0,15}(?:[^\s\r\n]*)<a href=\"\/wiki\/' + title + '(?:[^\s\r\n]*)(?:[\s\r\n]+[^\s\r\n]*){0,10}', 'ig');
			found_string = page_content.match(pattern);
			if(!found_string) {
				redo(retry_limit);
			} else {
				var replace_pattern = RegExp('(<a href=\"\/wiki\/' + title + '.*?<\/a>)', 'ig');
				found_string = found_string[0].replace(replace_pattern, '<span style=\'background-color: yellow\'>$1</span>');		
				//found_string = found_string[0];
				console.log('found ' + title_fm + ' in ' + data['query']['pages'][page_id]['title'])
				render();
			}
		}
	}

	function choose_page(err, pages) {
		var num = random_int(0, pages.length - 1);
		var page = pages[num];
		var page_content = do_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvparse&pageids=' + page + '&rvprop=content&format=json', process_page);
		console.log('loading pageid ' + page + '');
	}

	function render(err) {
		$(document).ready(function() {
			$('#phrase').html('<p><em>In the phrase</em></p><p>' + found_string + '</p>');
			$('#inst').html('<p><em>Does the highlighted link mean:</em></p>');
			for(var i = 0; i < choices.length; i++) {
				$('#as').append('<li>' + choices[i] + '</li>');
			}
			console.log('prepared html');
		});
	}

	do_query('http://en.wikipedia.org/w/api.php?action=query&list=backlinks&bltitle=' + title + '&prop=revisions&titles=' + title + '&rvprop=content&bllimit=500&format=json', process_backlinks);
}

function get_dabs() {
	do_query('http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Disambiguation_pages_with_links&prop=info&cmlimit=500&format=json', process_dabs);
}

function process_dabs(err, data) {
	var dabs = data['query']['categorymembers'];
	var todo = []
	console.log(dabs)
	for(var i = 0; i < dabs.length; i++) {
		todo.push(dabs[i]['title'].replace('Talk:', '').replace(/\s/gi, '_'))
	}
	
	var quiz = new dab(todo[random_int(0, todo.length - 1)]);
}

function redo(limit) {
	if(limit > 0 ) {
		retry_limit -= 1;
		console.log('Something is awry! ' + retry_limit +' retries left');
		get_dabs();
	} else {
		$('#phrase').html('<h1>I just give up....</h1>');
	}
	
}

get_dabs();