BenSearchConfig = {
	// Make sure to have this as a link or a dispatcher that can provide the desired content
	// The path within the indexed document root follows this URL.
	// In case of the link, make sure to also provide x and r rights so that your web server will be able to access the material
	'hit.origin': 'http://hq.scene.ro/books',

	// The ES host to which the UI interface can connect
	'es.host': 'hq.scene.ro:9200'
}