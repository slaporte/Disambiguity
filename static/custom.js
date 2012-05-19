$(document).ready(function() {

	var global_timeout = 5000;

	function do_query(url, complete_callback, kwargs) {
	    var all_kwargs = {
	        url: url,
	        type: 'get',
	        dataType: 'json',
	        timeout: global_timeout,
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
	    };

	    for (var key in kwargs) {
	        if(kwargs.hasOwnProperty(key)) {
	            all_kwargs[key] = kwargs[key];
	        }
	    }
	    $.ajax(all_kwargs);
	}

	do_query('http://localhost:8080/get/', page_setup);


	function page_setup(err, data){
		console.log(data)

		var dab 		= data;
		var choices 	= dab.choices,
			page_title	= dab.source_title,
			dab_title	= dab.title,
			dab_context	= dab.context,
			images 		= dab.images;
		$('#disambig_query').html(page_title);
		$('#disambig_page').html(dab_title);
		$('#context').html(dab_context);
		$('span:contains("disambiguation")"').parents('sup').hide();
		$('#option_list').empty();
		for(var i = 0; i < choices.length; i++) {
			$('#option_list').append('<li><div class="option med_bg"><span class="opt_title accent_text">' +  choices[i].title + '</span> - <span class="opt_desc">' + choices[i].text + '</span></div><div class="preview" link="http://en.m.wikipedia.org/wiki/' + choices[i].title.replace(' ', '_') + '"></div></li>');
		}
		$('.filmstrip_img').empty();
		for(var i = 0; i < images.length; i++) {
			$('.filmstrip_img').append('<img src="' + images[i].replace('//', 'http://') + '"/>');
		}

		ready_the_options();
	}

// VARIABLES /////////////////////////////
	var fullDuration = 2500;
	var slide_distance = $('div#left').width();
	var i = 1;
	var colors_array = [['#ebf2f6', '#DAF0FC', '#25b8eb'], ['#EAEAEF','#E1E1F4','#6161BC'], ['#EBF7F0','#BDF2D3','#2DAD86'],  ['#F4ECE9','#FCC4B6','#F76C48'], ['#ECF2E9','#C9E0B1','#87B52D']]
	var light = colors_array[0][0]
	var med = colors_array[0][1]
	var accent = colors_array[0][2]
	var bodytext = '#808285';
	var expandedWidth = "2200px";

// CACHE /////////////////////////////////
	var sectorwrapper = $('#sectorwrapper');
	var statsbar = $('div#statsbar')
	var back = $('#back')
	var topbar = $('#topbar')
	var bottombar = $('#bottombar')


// FUNCTIONS /////////////////////////////
	function resetContent() {
		
	}

	function resetStats() {
		$('div#statsbar h3').text("124,321 dabs completed!")
		// $('div#statsbar').delay(fullDuration*.1).animate({height: 40}, fullDuration*.2).delay(fullDuration*.5).animate({height: 8}, fullDuration*.2);
	}

	function resetLeft() {
		$('.preview').removeClass('viewing')
		topbar.css('margin-left', '80px');
		bottombar.css('margin-left', '80px');
		sectorwrapper.css('width', 0);
		sectorwrapper.css('left', '0px')
		back.css('visibility', 'hidden')
		$('.unpreview').removeClass('unpreview');
		document.getElementById('wikipedia_preview').src = '';
	}

	function swipe(i) {	
		$('header#question').animate({opacity: 0}, fullDuration*.2).delay(fullDuration*.7).animate({opacity: 1}, fullDuration*.1);
		topbar.animate({opacity: 0}, fullDuration*.2).delay(fullDuration*.7).animate({opacity: 1}, fullDuration*.1);	
		bottombar.animate({opacity: 0}, fullDuration*.2).delay(fullDuration*.7).animate({opacity: 1}, fullDuration*.1);	
		sectorwrapper.removeClass('sectorwrappertransition').delay(fullDuration*.3).animate({
			top: "-100%",
		}, fullDuration*.3, function() {
			resetLeft();
			resetContent();
			$('#option_list li').css("opacity", 1);
			sectorwrapper.css('top', '100%');
			sectorwrapper.animate({
				top: "0%",
			}, fullDuration*.3, function() {
				$('#sectorwrapper').addClass('sectorwrappertransition')
			});
		});


	}

	function colorChange(palette) {
		statsbar.delay(fullDuration*.1).animate({height: 40}, fullDuration*.2).animate({
		      backgroundColor: palette[2]
		}, fullDuration*.6, function() {}).delay(fullDuration*.1).animate({height: 8}, fullDuration*.2);;

		$('body').animate({
		      backgroundColor: palette[0]
		}, fullDuration*.6, function() {
			light = palette[0];
			med = palette[1];
			accent = palette[2];
			$('.light_bg').css('backgroundColor', light)
			$('.light_text').css('color', light)
			$('.accent_bg').css('backgroundColor', accent)
			$('.med_bg').css('backgroundColor', med)
			$('.med_text').css('color', med)
			$('.accent_text').css('color', accent)
			$('.accent_border').css('border-color', accent)

		});

		
	}


// BEHAVIORS ////////////////////////////////////////////////////

	window.onscroll = function(e) {
		console.log(e)
	}
	
	ready_the_options = function() {


		$('div.option').on({
			click: function() {
				$(this).parents('li').siblings('li').animate({
				    opacity: 0,
				}, 500);
				resetStats();	
				colorChange(colors_array[i]);	
				swipe(i);
				i++; //i rotates through the colors
				if (i == colors_array.length) {i=0;}
			},
			mouseover: function() {
				$(this).css('backgroundColor', accent)
				$(this).children('.opt_title').css('color', "white")
				$(this).children('.opt_desc').css('color', light)
					
			},
			mouseleave: function() {
				$(this).css('backgroundColor', med)
				$(this).children('.opt_title').css('color', accent);
				$(this).children('.opt_desc').css('color', bodytext);
			}
		});

		$('#option_list li').on({
			mouseenter: function(){
				$(this).addClass('active')
			},
			mouseleave: function(){
				$(this).removeClass('active')
			}
		});

		$('div.preview').on({
			click: function(){
				$('.preview').removeClass('viewing')
				$(this).addClass('viewing')
				if (sectorwrapper.css('left') == "0px") {
					topbar.css('margin-left', "-"+(slide_distance-80)+"px");
					bottombar.css('margin-left', "-"+(slide_distance-80)+"px");
					sectorwrapper.css('width', expandedWidth)
					sectorwrapper.css('left', "-"+slide_distance+"px")
				}
				var location = $(this).attr('link')
				back.css('visibility', 'visible');
				back.animate({opacity: 1}, 600, function() {
					document.getElementById('wikipedia_preview').src = location;
				});
			}
		});
		
		back.on({
			click: function(){
				resetLeft();
			}
		});

		$('#skip').on({
			click: function(){
				swipe(i);	
			}
		});

		statsbar.on({
			mouseenter: function(){
				statsbar.delay(200).animate({height: 40}, 200)
			},
			mouseleave: function(){
				statsbar.stop(true, true);
				statsbar.animate({height: 8}, 200)
			}
		});

		$('a').on({ //to override default link colors
			mouseenter: function(){
				$(this).addClass('accent_text')
			},
			mouseleave: function(){
				$(this).removeClass('accent_text')
		    }
		});

	}
// INITIALIZING THE PAGE ///////////////////////
	ready_the_options();
	resetContent();
	// resetStats();

});