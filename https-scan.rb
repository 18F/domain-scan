#!/usr/bin/env ruby

require 'rubygems'
require 'csv'
require 'site-inspector'
require 'oj'

INPUT_CSV = ARGV[0] || "gov-domains.csv"

def go
  CSV.open("analysis.csv", "w") do |analysis|

    analysis << [
      "domain",
      "agency",
      "https",
      "force_https",
      "hsts",
      "hsts details"
    ]

    # gov-domains.csv is the CSV of domains distributed here:
    # http://catalog.data.gov/dataset/gov-domains-api
    CSV.foreach(INPUT_CSV) do |row|
      # next unless row[0]
      # next if row[0].strip.downcase == "domain name"

      domain = row[1].strip.downcase
      agency = row[2] ? row[2].strip : nil
      puts "[#{domain}]"

      puts "\t[#{domain}]"
      output = details_for domain, agency
      analysis << output
    end
  end
end

def cache_path(domain)
  "cache/#{domain}.json"
end

def cache!(response, domain)
  File.open(cache_path(domain), "w") {|f| f.write Oj.dump(response)}
end

def uncache!(domain)
  if File.exists?(cache_path(domain))
    Oj.load(File.read(cache_path(domain)))
  end
end

def details_for(domain, agency)
  if cached = uncache!(domain)
    puts "\tCached, skipping."
    return cached
  end

  begin
    site = SiteInspector.new domain
  rescue Exception => exc
    puts "\tERROR."
    puts exc
    return []
  end

  hsts = nil
  if site.response
    strict_header = site.response.headers.keys.find {|h| h.downcase =~ /^strict/}
    if strict_header
      hsts = site.response.headers[strict_header]
    end
  end

  response = [
    domain,
    agency,
    site.https?,
    site.enforce_https?,
    !!hsts,
    (hsts || "N/A")
  ]

  cache! response, domain

  puts "\tFetched, cached."

  response
end

go
